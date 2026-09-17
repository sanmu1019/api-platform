from __future__ import annotations

import hashlib
import time
import uuid
from collections import defaultdict, deque
from ipaddress import ip_address
from typing import Deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.database import get_conn


_LOG_SKIP_PATHS = {"/health", "/favicon.ico"}
_LOG_SKIP_PREFIXES = ("/static/", "/frontend/")
# 除 /api/ 前缀之外，额外需要限流的路径：自助注册会写库，可被脚本无限刷。
_LIMITED_EXACT_PATHS = {"/register/key"}

# 日志/统计里保留的 Api-Key 明文字段长度；短于该长度时连前缀都不给。
_KEY_PREFIX_LEN = 8


def mask_api_key(key: str | None) -> str:
    """把 Api-Key 脱敏成"可对账、不可还原"的形式。

    日志和统计只需要区分"哪个 Key 调了多少次"，不需要完整凭据 ——
    原先直接存明文，导出一份日志或备份就等于泄露 Key。

    保留前 8 位便于人工核对是哪个 Key，其余用 sha256 前 12 位代替；
    同一 Key 永远得到同一结果，所以按 Key 分组统计不受影响。
    Key 本身较短时（比如默认的 test123）连前缀都不给，避免把整个 Key 暴露出去。
    """
    if not key:
        return ""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    if len(key) >= _KEY_PREFIX_LEN * 2:
        return f"{key[:_KEY_PREFIX_LEN]}…{digest}"
    return f"…{digest}"


def _is_trusted_proxy_host(host: str) -> bool:
    if host in {"localhost", "testclient"}:
        return True
    try:
        parsed = ip_address(host)
    except ValueError:
        return False
    return parsed.is_loopback or parsed.is_private


def client_ip(request: Request) -> str:
    peer = request.client.host if request.client else ""
    if _is_trusted_proxy_host(peer):
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip", "")
        if real_ip:
            return real_ip.strip()
    return peer or "unknown"


def _should_log_access(path: str) -> bool:
    return path not in _LOG_SKIP_PATHS and not path.startswith(_LOG_SKIP_PREFIXES)


def security_headers() -> dict[str, str]:
    """公开响应应带的加固头。

    抽成函数是因为 500 由最外层的 `ServerErrorMiddleware` 产生 —— 它在
    `SecurityHeadersMiddleware` **之外**，异常沿着中间件栈往外抛时
    SecurityHeadersMiddleware 根本拿不到响应对象，所以 500 需要自己补。
    """
    if not settings.public_security_enabled:
        return {}
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
    if settings.is_production:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for name, value in security_headers().items():
            response.headers.setdefault(name, value)
        return response


class AdminIPAllowlistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        allowlist = settings.admin_ip_allowlist_values
        if allowlist and request.url.path.startswith(settings.normalized_admin_path):
            ip = client_ip(request)
            if ip not in allowlist:
                return JSONResponse(status_code=403, content={"detail": "当前 IP 不允许访问后台"})
        return await call_next(request)


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            if _should_log_access(request.url.path):
                try:
                    with get_conn() as conn:
                        conn.execute(
                            """
                            INSERT INTO access_logs(method, path, status_code, duration_ms, client_ip, user_agent, api_key)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                request.method,
                                request.url.path,
                                status_code,
                                duration_ms,
                                client_ip(request),
                                request.headers.get("user-agent", ""),
                                # 存脱敏值：日志泄露不应该等于 Key 泄露
                                mask_api_key(request.headers.get("Api-Key") or request.headers.get("X-API-Key")),
                            ),
                        )
                except Exception:
                    # 访问日志不能影响主请求。
                    pass


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.window_seconds = 60
        self.limit = max(0, int(settings.rate_limit_per_minute or 0))
        self.bucket: dict[str, Deque[float]] = defaultdict(deque)
        self._last_sweep = time.time()

    @staticmethod
    def _is_limited_path(path: str) -> bool:
        # /register/key 会写库，必须一起限流；原先只拦 /api/ 前缀，导致它可以被无限刷。
        return path.startswith("/api/") or path in _LIMITED_EXACT_PATHS

    def _sweep(self, now: float) -> None:
        """回收过期的限流桶。

        桶的键是 `ip:api-key` 组合，长时间运行会不断累积；不回收就等于内存泄漏，
        而且每个新组合都能稳定占用一个 deque，可被用来慢慢耗尽内存。
        每 window_seconds 最多扫一次，均摊开销可忽略。
        """
        if now - self._last_sweep < self.window_seconds:
            return
        self._last_sweep = now
        stale = [
            key
            for key, q in self.bucket.items()
            if not q or now - q[-1] > self.window_seconds
        ]
        for key in stale:
            self.bucket.pop(key, None)

    async def dispatch(self, request: Request, call_next):
        if self.limit <= 0 or not self._is_limited_path(request.url.path):
            return await call_next(request)

        key = f"{client_ip(request)}:{request.headers.get('Api-Key') or request.headers.get('X-API-Key') or ''}"
        now = time.time()
        self._sweep(now)
        q = self.bucket[key]
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        if len(q) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": f"请求过于频繁，请稍后再试（限制：{self.limit}/分钟）"},
                headers={"Retry-After": "60"},
            )
        q.append(now)
        return await call_next(request)

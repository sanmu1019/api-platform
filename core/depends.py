from __future__ import annotations

import hashlib
import hmac
import time
from datetime import date
from hmac import compare_digest
from typing import Annotated

from fastapi import Cookie, Header, HTTPException, Request, status

from core.config import settings
from core.database import get_conn
from core.middleware import client_ip, mask_api_key


def _extract_api_key(api_key: str | None, x_api_key: str | None) -> str | None:
    return api_key or x_api_key


ADMIN_SESSION_TTL = 60 * 60 * 8


def _sign_admin_session(expires_at: int) -> str:
    return hmac.new(settings.admin_token.encode(), f"admin:{expires_at}".encode(), hashlib.sha256).hexdigest()


def make_admin_session() -> str:
    """后台登录 Cookie：`过期时间.签名`，不含 admin_token 原文；更换 admin_token 后旧会话自动失效。"""
    expires_at = int(time.time()) + ADMIN_SESSION_TTL
    return f"{expires_at}.{_sign_admin_session(expires_at)}"


def _valid_admin_session(value: str) -> bool:
    expires_at, _, sig = value.partition(".")
    if not expires_at.isdigit() or int(expires_at) < time.time():
        return False
    return compare_digest(sig, _sign_admin_session(int(expires_at)))


def verify_api_key_value(request: Request, key: str | None = None, api_name: str | None = None) -> str:
    """公开接口免鉴权。

    当前项目按“公开可用 API 门户”方式运行：
    - 业务接口默认不强制要求 `Api-Key` / `X-API-Key`
    - 仍会检查接口是否被后台停用
    - 仍会记录调用统计，未传 key 时记为 `public`

    保留该函数名是为了兼容现有路由和动态接口逻辑。
    """
    if api_name is None:
        route = request.scope.get("route")
        api_name = route.name if route else ""

    supplied_key = (key or "").strip()
    today = date.today().isoformat()
    with get_conn() as conn:
        api = conn.execute("SELECT enabled FROM apis WHERE name = ?", (api_name,)).fetchone()
        if api and not api["enabled"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="接口已停用")

        if supplied_key:
            api_key = conn.execute(
                """
                SELECT key, enabled, quota_per_day
                FROM api_keys
                WHERE key = ?
                """,
                (supplied_key,),
            ).fetchone()
            if not api_key:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Api-Key 无效")
            if not api_key["enabled"]:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Api-Key 已停用")

            # 额度校验与计数自增必须合并成一条语句。
            # 原来的"读 used_today -> 判断 -> 写回 used_today+1"在并发下会互相覆盖：
            # 两个请求同时读到 N，都认为没超额，最后都写回 N+1，实际放了两次量。
            # 改成带条件的 UPDATE 后，判断和自增在同一个原子步骤里完成，
            # 条件不满足时 rowcount 为 0，即额度已用尽。
            quota = int(api_key["quota_per_day"] or 0)
            consumed = conn.execute(
                """
                UPDATE api_keys
                SET used_today = CASE WHEN last_used_date = ? THEN COALESCE(used_today, 0) + 1 ELSE 1 END,
                    last_used_date = ?
                WHERE key = ?
                  AND (? <= 0 OR last_used_date != ? OR COALESCE(used_today, 0) < ?)
                """,
                (today, today, supplied_key, quota, today, quota),
            )
            if consumed.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Api-Key 今日额度已用尽")

            # 统计里只记脱敏值；上面的 UPDATE 仍用明文 Key 做条件，鉴权逻辑不受影响。
            stat_key = mask_api_key(supplied_key)
        else:
            if settings.require_api_key:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Api-Key")
            stat_key = "public"

        conn.execute(
            """
            INSERT INTO api_stats(api_name, api_key, path, client_ip)
            VALUES (?, ?, ?, ?)
            """,
            (
                api_name or "unknown",
                stat_key,
                str(request.url.path),
                client_ip(request),
            ),
        )
    return stat_key


def verify_api_key(
    request: Request,
    api_key: Annotated[str | None, Header(alias="Api-Key", convert_underscores=False)] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key", convert_underscores=False)] = None,
) -> str:
    return verify_api_key_value(request, _extract_api_key(api_key, x_api_key))


def verify_admin_token(
    admin_token: Annotated[str | None, Header(alias="Admin-Token", convert_underscores=False)] = None,
    admin_cookie: Annotated[str | None, Cookie(alias="admin_token")] = None,
) -> str:
    if not admin_token and admin_cookie:
        if _valid_admin_session(admin_cookie):
            return "admin"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    token = admin_token or ""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Admin-Token")
    if not compare_digest(token, settings.admin_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin-Token 错误")
    return token

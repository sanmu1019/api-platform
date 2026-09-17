from __future__ import annotations

import json
import re
import sqlite3
import time
from collections import defaultdict, deque
from io import StringIO
from hmac import compare_digest
from typing import Any
import csv
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from core.config import settings
from core.database import API_PRESENTATION, DEFAULT_SITE_SETTINGS, get_conn
from core.depends import verify_admin_token
from core.middleware import client_ip
from core.routing import api_route_index, route_exists

router = APIRouter(prefix=settings.normalized_admin_path, tags=["admin"])

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,63}$")
_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
_RESPONSE_TYPES = {"json", "text", "html"}
_BUILTIN_LOCKED_FIELDS = {"path", "method", "response_type", "response_body", "status_code"}
_LOGIN_FAILS: dict[str, deque[float]] = defaultdict(deque)
_LOGIN_FAILS_SWEPT_AT = 0.0
_SITE_SETTING_KEYS = {"site_name", "logo_text", "hero_title", "hero_subtitle"}
_SITE_SETTING_LIMITS = {"site_name": 80, "logo_text": 12, "hero_title": 160, "hero_subtitle": 500}

ADMIN_SITE_FALLBACK = DEFAULT_SITE_SETTINGS
ADMIN_API_PRESENTATION = API_PRESENTATION

# 与 main.py 中同名函数保持一致：单个 "?" 是合法标点，只有连续多个才说明是解码乱码。
_BROKEN_MARKERS = ("锟", "\ufffd", "鏈", "鍚", "璇", "閹", "鐠", "閸")
_MOJIBAKE_RE = re.compile(r"\?{2,}")


def _looks_broken_text(value: str | None) -> bool:
    text = value or ""
    if not text:
        return True
    if any(marker in text for marker in _BROKEN_MARKERS):
        return True
    return bool(_MOJIBAKE_RE.search(text))


def _clean_site_settings_for_admin(data: dict[str, str]) -> dict[str, str]:
    fixed = dict(ADMIN_SITE_FALLBACK)
    fixed.update({k: v for k, v in data.items() if v and not _looks_broken_text(v)})
    return fixed


def _clean_api_row_for_admin(row: dict) -> dict:
    title, description, category = ADMIN_API_PRESENTATION.get(row.get("name"), ("", "", ""))
    if title and _looks_broken_text(row.get("title")):
        row["title"] = title
    if description and _looks_broken_text(row.get("description")):
        row["description"] = description
    if category and _looks_broken_text(row.get("category")):
        row["category"] = category
    return row



def _site_settings(conn) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM site_settings").fetchall()
    data = {row["key"]: row["value"] for row in rows}
    defaults = dict(ADMIN_SITE_FALLBACK)
    defaults.update({k: v for k, v in data.items() if k in _SITE_SETTING_KEYS})
    return defaults

def _clean_site_value(key: str, value: str) -> str:
    value = (value or "").strip()
    limit = _SITE_SETTING_LIMITS[key]
    if not value:
        return ADMIN_SITE_FALLBACK[key]
    if len(value) > limit:
        raise HTTPException(status_code=400, detail=f"{key} must be {limit} characters or fewer")
    return value

def _validate_name(name: str) -> str:
    name = name.strip()
    if not _NAME_RE.fullmatch(name):
        raise HTTPException(status_code=400, detail="API name must be 2-64 characters and start with a letter")
    return name


def _validate_path(name: str, path: str) -> str:
    path = path.strip()
    expected = f"/api/{name}"
    legacy = f"/api/custom/{name}"
    if path not in {expected, legacy}:
        raise HTTPException(status_code=400, detail=f"自定义接口路径必须为 {expected} 或兼容路径 {legacy}")
    return path


def _validate_method(method: str) -> str:
    method = method.strip().upper()
    if method not in _METHODS:
        raise HTTPException(status_code=400, detail="不支持的 HTTP 方法")
    return method


def _validate_response(response_type: str, response_body: str) -> tuple[str, str]:
    response_type = response_type.strip().lower()
    if response_type not in _RESPONSE_TYPES:
        raise HTTPException(status_code=400, detail="响应类型只能是 json、text 或 html")
    if response_type == "json":
        try:
            json.loads(response_body or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail='JSON 响应内容格式错误；模板变量请放在字符串中，例如 "{{query.name}}"') from exc
    return response_type, response_body


def _validate_status_code(status_code: int) -> int:
    if not 100 <= status_code <= 599:
        raise HTTPException(status_code=400, detail="状态码必须在 100-599 之间")
    return status_code


def _changed(value: Any) -> bool:
    return value is not None


def _sweep_login_fails(now: float) -> None:
    """回收过期的登录失败记录。

    键是客户端 IP，攻击者不断换 IP 就能持续堆积，不回收同样会缓慢吃内存。
    每 window 秒最多扫一次。
    """
    global _LOGIN_FAILS_SWEPT_AT
    window = max(1, settings.admin_login_fail_window_seconds)
    if now - _LOGIN_FAILS_SWEPT_AT < window:
        return
    _LOGIN_FAILS_SWEPT_AT = now
    stale = [ip for ip, q in _LOGIN_FAILS.items() if not q or now - q[-1] > window]
    for ip in stale:
        _LOGIN_FAILS.pop(ip, None)


@router.post("/login")
def login(
    response: Response,
    request: Request,
    payload: dict[str, str] | None = Body(default=None),
    token: str | None = Query(default=None),
) -> dict:
    token = token or ((payload or {}).get("token") or "")
    if not token:
        raise HTTPException(status_code=400, detail="Admin-Token 不能为空")
    ip = client_ip(request)
    now = time.time()
    window = max(1, settings.admin_login_fail_window_seconds)
    _sweep_login_fails(now)
    q = _LOGIN_FAILS[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= max(1, settings.admin_login_fail_limit):
        raise HTTPException(status_code=429, detail="登录失败次数过多，请稍后再试")

    if not compare_digest(token, settings.admin_token):
        q.append(now)
        raise HTTPException(status_code=403, detail="Admin-Token 错误")
    q.clear()
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=60 * 60 * 8,
        path="/",
    )
    return {
        "code": 200,
        "msg": "登录成功",
        "data": {"user": "admin", "expires_in": 60 * 60 * 8, "login_ip": ip},
    }


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie("admin_token", path="/")
    return {"code": 200, "msg": "logged out"}


@router.get("/session", dependencies=[Depends(verify_admin_token)])
def session() -> dict:
    return {"code": 200, "msg": "ok", "data": {"user": "admin", "expires_in": 60 * 60 * 8}}


@router.get("/site-settings", dependencies=[Depends(verify_admin_token)])
def get_site_settings() -> dict:
    with get_conn() as conn:
        data = _clean_site_settings_for_admin(_site_settings(conn))
    return {"code": 200, "msg": "success", "data": data}


@router.patch("/site-settings", dependencies=[Depends(verify_admin_token)])
def update_site_settings(payload: dict[str, str]) -> dict:
    unknown = set(payload) - _SITE_SETTING_KEYS
    if unknown:
        raise HTTPException(status_code=400, detail=f"不支持的站点配置项：{', '.join(sorted(unknown))}")
    if not payload:
        raise HTTPException(status_code=400, detail="没有可更新的站点配置")
    cleaned = {key: _clean_site_value(key, str(value)) for key, value in payload.items()}
    with get_conn() as conn:
        for key, value in cleaned.items():
            conn.execute(
                """
                INSERT INTO site_settings(key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
        data = _clean_site_settings_for_admin(_site_settings(conn))
    return {"code": 200, "msg": "站点配置已更新", "data": data}


@router.get("", response_class=HTMLResponse)
def admin_home() -> str:
    return Path("frontend/admin.html").read_text(encoding="utf-8")

@router.get("/apis", dependencies=[Depends(verify_admin_token)])
def list_apis() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT name, path, title, description, category, method,
                   response_type, response_body, status_code, enabled, is_builtin, sort_order
            FROM apis
            ORDER BY sort_order ASC, name ASC
            """
        ).fetchall()
    return {"code": 200, "data": [_clean_api_row_for_admin(dict(row)) for row in rows]}


@router.get("/categories", dependencies=[Depends(verify_admin_token)])
def categories() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT category, COUNT(*) AS total,
                   SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) AS enabled
            FROM apis
            GROUP BY category
            ORDER BY category
            """
        ).fetchall()
    data = []
    for row in rows:
        item = dict(row)
        if _looks_broken_text(item.get("category")):
            item["category"] = "\u9ed8\u8ba4\u5206\u7c7b"
        data.append(item)
    return {"code": 200, "data": data}


@router.get("/route-check", dependencies=[Depends(verify_admin_token)])
def route_check(request: Request) -> dict:
    route_paths, route_names = api_route_index(request.app)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name, path, title, is_builtin FROM apis ORDER BY sort_order ASC, name ASC"
        ).fetchall()

    data = []
    for row in rows:
        exists = route_exists(route_paths, route_names, row["name"], row["path"], bool(row["is_builtin"]))
        clean = _clean_api_row_for_admin(dict(row))
        data.append(
            {
                "name": clean["name"],
                "title": clean["title"],
                "path": clean["path"],
                "is_builtin": clean["is_builtin"],
                "route_exists": bool(exists),
            }
        )
    return {"code": 200, "data": data}


@router.post("/apis", dependencies=[Depends(verify_admin_token)])
def create_api(
    name: str,
    path: str,
    title: str,
    description: str,
    category: str = "自定义",
    method: str = "GET",
    response_type: str = "json",
    response_body: str = "{}",
    status_code: int = 200,
    sort_order: int = 100,
    enabled: bool = True,
) -> dict:
    name = _validate_name(name)
    path = _validate_path(name, path)
    method = _validate_method(method)
    response_type, response_body = _validate_response(response_type, response_body)
    status_code = _validate_status_code(status_code)
    if not title.strip() or not description.strip():
        raise HTTPException(status_code=400, detail="Title and description are required")
    with get_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO apis(
                    name, path, title, description, category, method,
                    response_type, response_body, status_code, enabled, is_builtin, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (name, path, title.strip(), description.strip(), category.strip() or "自定义", method, response_type, response_body, status_code, 1 if enabled else 0, sort_order),
            )
        except sqlite3.IntegrityError as exc:
            # 只把主键/唯一约束冲突解释成"已存在"。
            # 原先捕获的是 Exception，数据库锁、磁盘错误之类也会被伪装成 400
            # "参数非法"，线上排查时完全看不出真实原因。
            raise HTTPException(status_code=400, detail="API 名称或路径已存在") from exc
    return {"code": 200, "msg": "成功", "data": {"name": name, "path": path, "doc": f"/doc/{name}.html"}}


@router.patch("/apis/{name}", dependencies=[Depends(verify_admin_token)])
def update_api(
    name: str,
    enabled: bool | None = Query(None),
    path: str | None = None,
    title: str | None = None,
    description: str | None = None,
    category: str | None = None,
    method: str | None = None,
    response_type: str | None = None,
    response_body: str | None = None,
    status_code: int | None = None,
    sort_order: int | None = None,
) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM apis WHERE name = ?", (name,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Resource not found")
        if row["is_builtin"] and any(
            _changed(value)
            for field, value in {"path": path, "method": method, "response_type": response_type, "response_body": response_body, "status_code": status_code}.items()
            if field in _BUILTIN_LOCKED_FIELDS
        ):
            raise HTTPException(status_code=400, detail="Built-in API route, method, and response settings cannot be modified")
        if path is not None:
            path = _validate_path(name, path)
        if method is not None:
            method = _validate_method(method)
        if response_type is not None or response_body is not None:
            next_type = response_type if response_type is not None else row["response_type"]
            next_body = response_body if response_body is not None else row["response_body"]
            response_type, response_body = _validate_response(next_type, next_body)
        if status_code is not None:
            status_code = _validate_status_code(status_code)
        conn.execute(
            """
            UPDATE apis
            SET path = COALESCE(?, path),
                title = COALESCE(?, title),
                description = COALESCE(?, description),
                category = COALESCE(?, category),
                method = COALESCE(?, method),
                response_type = COALESCE(?, response_type),
                response_body = COALESCE(?, response_body),
                status_code = COALESCE(?, status_code),
                sort_order = COALESCE(?, sort_order),
                enabled = COALESCE(?, enabled),
                updated_at = CURRENT_TIMESTAMP
            WHERE name = ?
            """,
            (path, title.strip() if title is not None else None, description.strip() if description is not None else None, category.strip() if category is not None else None, method, response_type, response_body, status_code, sort_order, 1 if enabled is True else 0 if enabled is False else None, name),
        )
    return {"code": 200, "msg": "成功", "data": {"name": name, "enabled": enabled}}


@router.delete("/apis/{name}", dependencies=[Depends(verify_admin_token)])
def delete_api(name: str) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT is_builtin FROM apis WHERE name = ?", (name,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Resource not found")
        if row["is_builtin"]:
            raise HTTPException(status_code=400, detail="Built-in APIs cannot be deleted")
        conn.execute("DELETE FROM apis WHERE name = ?", (name,))
    return {"code": 200, "msg": "成功"}


@router.get("/keys", dependencies=[Depends(verify_admin_token)])
def list_keys() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT key, name, enabled, quota_per_day, used_today, last_used_date, created_at
            FROM api_keys
            ORDER BY name
            """
        ).fetchall()
    return {"code": 200, "data": [dict(row) for row in rows]}


@router.post("/keys", dependencies=[Depends(verify_admin_token)])
def create_key(key: str, name: str = "new user", quota_per_day: int = 0) -> dict:
    key = key.strip()
    name = name.strip() or "new user"
    if not key:
        raise HTTPException(status_code=400, detail="Key is required")
    if quota_per_day < 0:
        raise HTTPException(status_code=400, detail="Daily quota cannot be negative")
    with get_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO api_keys(key, name, enabled, quota_per_day, created_at)
                VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
                """,
                (key, name, quota_per_day),
            )
        except sqlite3.IntegrityError as exc:
            # 同上：只把唯一约束冲突当成"Key 已存在"，其余异常交给全局处理器记录堆栈。
            raise HTTPException(status_code=400, detail="Key 已存在") from exc
    return {"code": 200, "msg": "成功", "data": {"key": key, "name": name, "enabled": 1, "quota_per_day": quota_per_day}}


@router.patch("/keys/{key}", dependencies=[Depends(verify_admin_token)])
def update_key(key: str, enabled: bool | None = Query(None), quota_per_day: int | None = Query(None)) -> dict:
    if quota_per_day is not None and quota_per_day < 0:
        raise HTTPException(status_code=400, detail="Daily quota cannot be negative")
    with get_conn() as conn:
        cur = conn.execute(
            """
            UPDATE api_keys
            SET enabled = COALESCE(?, enabled),
                quota_per_day = COALESCE(?, quota_per_day)
            WHERE key = ?
            """,
            (1 if enabled is True else 0 if enabled is False else None, quota_per_day, key),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Resource not found")
    return {"code": 200, "msg": "成功", "data": {"key": key, "enabled": enabled, "quota_per_day": quota_per_day}}


@router.delete("/keys/{key}", dependencies=[Depends(verify_admin_token)])
def delete_key(key: str) -> dict:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM api_keys WHERE key = ?", (key,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Resource not found")
    return {"code": 200, "msg": "成功"}


@router.get("/stats", dependencies=[Depends(verify_admin_token)])
def stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS total FROM api_stats").fetchone()["total"]
        access_total = conn.execute("SELECT COUNT(*) AS total FROM access_logs").fetchone()["total"]
        error_total = conn.execute("SELECT COUNT(*) AS total FROM access_logs WHERE status_code >= 400").fetchone()["total"]
        by_api = conn.execute(
            """
            SELECT api_name, COUNT(*) AS count
            FROM api_stats
            GROUP BY api_name
            ORDER BY count DESC
            """
        ).fetchall()
        by_key = conn.execute(
            """
            SELECT api_key, COUNT(*) AS count
            FROM api_stats
            GROUP BY api_key
            ORDER BY count DESC
            """
        ).fetchall()
        keys = conn.execute("SELECT key, name, enabled FROM api_keys ORDER BY name").fetchall()
        recent = conn.execute(
            """
            SELECT method, path, status_code, duration_ms, client_ip, created_at
            FROM access_logs
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()
    return {
        "code": 200,
        "data": {
            "total": total,
            "access_total": access_total,
            "error_total": error_total,
            "by_api": [dict(row) for row in by_api],
            "by_key": [dict(row) for row in by_key],
            "api_keys": [dict(row) for row in keys],
            "recent_access": [dict(row) for row in recent],
        },
    }


@router.get("/douyin-health", dependencies=[Depends(verify_admin_token)])
def douyin_health() -> dict:
    """抖音解析健康状态。

    `a_bogus` 是逆向签名，抖音换算法会导致解析**持续**失败，且症状和
    "链接失效"一模一样。把连续失败次数暴露出来，才能接监控告警
    （例如连续失败 >= 3 就报警），而不是等用户反馈才发现。
    """
    if not settings.enable_douyin:
        return {"code": 200, "msg": "disabled", "data": {"enabled": False}}

    # 延迟导入：enable_douyin 为 false 时不需要拉起抖音模块。
    from apis.douyin.detail_api import signature_health

    return {"code": 200, "msg": "success", "data": {"enabled": True, **signature_health()}}


@router.get("/access-logs", dependencies=[Depends(verify_admin_token)])
def access_logs(limit: int = Query(50, ge=1, le=500), status_min: int | None = None) -> dict:
    sql = """
        SELECT id, method, path, status_code, duration_ms, client_ip, user_agent, api_key, created_at
        FROM access_logs
    """
    params: list[Any] = []
    if status_min is not None:
        sql += " WHERE status_code >= ?"
        params.append(status_min)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"code": 200, "data": [dict(row) for row in rows]}


_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value: Any) -> Any:
    """防 CSV 公式注入。

    user_agent / path 等字段完全由调用方控制，若以 = + - @ 开头，
    用 Excel 打开导出文件时会被当作公式执行。加前缀单引号使其保持文本。
    """
    if not isinstance(value, str) or not value:
        return value
    if value.startswith(_CSV_FORMULA_PREFIXES):
        return "'" + value
    return value


@router.get("/access-logs.csv", dependencies=[Depends(verify_admin_token)])
def access_logs_csv(limit: int = Query(1000, ge=1, le=10000), status_min: int | None = None):
    data = access_logs(limit=limit, status_min=status_min)["data"]
    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "method", "path", "status_code", "duration_ms", "client_ip", "user_agent", "api_key", "created_at"],
    )
    writer.writeheader()
    writer.writerows({key: _csv_safe(value) for key, value in row.items()} for row in data)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="access_logs.csv"'},
    )


@router.get("/backup/database", dependencies=[Depends(verify_admin_token)])
def backup_database():
    path = Path(settings.database_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="数据库文件不存在")
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=path.name,
    )


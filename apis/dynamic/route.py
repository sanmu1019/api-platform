import json
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from core.database import get_conn
from core.depends import verify_api_key_value

router = APIRouter(prefix="/api/custom", tags=["custom"])
short_router = APIRouter(prefix="/api", tags=["custom"])
_TEMPLATE_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")


def _api_detail(slug: str) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT name, title, description, method, response_type, response_body, status_code, enabled
            FROM apis
            WHERE name = ? AND is_builtin = 0
            """,
            (slug,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="接口不存在")
    if not row["enabled"]:
        raise HTTPException(status_code=403, detail="接口已停用")
    return dict(row)


async def _template_context(slug: str, request: Request) -> dict[str, Any]:
    body_text = ""
    body_json: Any = None
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        raw = await request.body()
        body_text = raw.decode("utf-8", errors="replace")
        content_type = request.headers.get("content-type", "")
        if body_text and "application/json" in content_type:
            try:
                body_json = json.loads(body_text)
            except json.JSONDecodeError:
                body_json = None

    now = datetime.now(timezone.utc)
    return {
        "slug": slug,
        "method": request.method,
        "path": request.url.path,
        "query": dict(request.query_params),
        "headers": dict(request.headers),
        "body": body_text,
        "json": body_json if body_json is not None else {},
        "client": {"host": request.client.host if request.client else ""},
        "now": {"iso": now.isoformat(), "timestamp": int(now.timestamp())},
    }


def _lookup(context: dict[str, Any], key: str) -> Any:
    current: Any = context
    for part in key.split("."):
        if isinstance(current, dict):
            current = current.get(part, "")
        else:
            return ""
    return current


def _render_template(template: str, context: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = _lookup(context, match.group(1))
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    return _TEMPLATE_RE.sub(replace, template)


async def _handle_custom_api(
    slug: str,
    request: Request,
):
    api = _api_detail(slug)
    verify_api_key_value(request, api_name=api["name"])
    expected_method = (api.get("method") or "GET").upper()
    if request.method != expected_method:
        raise HTTPException(status_code=405, detail=f"请使用 {expected_method} 方法请求该接口")

    context = await _template_context(slug, request)
    body = _render_template(api["response_body"] or "{}", context)
    status_code = int(api.get("status_code") or 200)

    if api["response_type"] == "text":
        return PlainTextResponse(body, status_code=status_code)
    if api["response_type"] == "html":
        return HTMLResponse(body, status_code=status_code)

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="接口响应 JSON 配置错误") from exc

    return Response(
        content=json.dumps({"code": status_code, "msg": "成功", "data": data}, ensure_ascii=False),
        status_code=status_code,
        media_type="application/json",
    )


@router.api_route(
    "/{slug}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    name="custom",
    response_model=None,
)
async def custom_api(
    slug: str,
    request: Request,
):
    return await _handle_custom_api(slug, request)


@short_router.api_route(
    "/{slug}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    name="custom_short",
    response_model=None,
)
async def custom_api_short(
    slug: str,
    request: Request,
):
    return await _handle_custom_api(slug, request)

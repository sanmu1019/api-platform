from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import secrets
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from admin.route import router as admin_router
from apis import register_api_routers
from core.config import settings
from core.database import API_PRESENTATION, DEFAULT_SITE_SETTINGS, get_conn, init_db
from core.exceptions import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from core.middleware import AccessLogMiddleware, AdminIPAllowlistMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware

SITE_FALLBACK = DEFAULT_SITE_SETTINGS

def _looks_broken_text(value: str | None) -> bool:
    text = value or ""
    broken_markers = ("?", "锟", "\ufffd", "鏈", "鍚", "璇", "閹", "鐠", "閸")
    return not text or any(marker in text for marker in broken_markers)


def _clean_site_settings(site: dict[str, str]) -> dict[str, str]:
    data = dict(SITE_FALLBACK)
    data.update({k: v for k, v in site.items() if v and not _looks_broken_text(v)})
    return data


def _clean_api_row(row: dict) -> dict:
    title, description, category = API_PRESENTATION.get(row.get("name"), ("", "", ""))
    if title and _looks_broken_text(row.get("title")):
        row["title"] = title
    if description and _looks_broken_text(row.get("description")):
        row["description"] = description
    if category and _looks_broken_text(row.get("category")):
        row["category"] = category
    return row


def _builtin_presentation_row(name: str) -> dict:
    title, description, category = API_PRESENTATION[name]
    path = "/api/douyin/parse" if name == "douyin_parse" else f"/api/{name}"
    method = "GET/POST" if name == "douyin_parse" else "GET"
    return {
        "name": name,
        "path": path,
        "title": title,
        "description": description,
        "category": category,
        "method": method,
        "response_type": "json",
        "response_body": "{}",
        "status_code": 200,
        "enabled": 1,
        "is_builtin": 1,
        "calls": 0,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate startup settings and initialize storage."""
    settings.validate_public_security()
    init_db()
    yield


def _read_frontend_page(filename: str) -> HTMLResponse:
    path = Path("frontend") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return HTMLResponse(path.read_text(encoding="utf-8"))



def _public_site_settings(conn) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM site_settings").fetchall()
    data = dict(SITE_FALLBACK)
    data.update({row["key"]: row["value"] for row in rows})
    return data

def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="API aggregation platform with public endpoints, documentation, testing, statistics, and admin tools.",
        version="1.1.0",
        lifespan=lifespan,
    )

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AdminIPAllowlistMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(AccessLogMiddleware)

    register_api_routers(app)
    app.include_router(admin_router)

    @app.get("/", include_in_schema=False)
    def home() -> HTMLResponse:
        return _read_frontend_page("index.html")

    @app.get("/portal/apis", include_in_schema=False)
    def portal_apis() -> dict:
        with get_conn() as conn:
            apis = conn.execute(
                """
                SELECT a.name, a.path, a.title, a.description, a.category, a.method,
                       a.response_type, a.response_body, a.status_code, a.enabled, a.is_builtin,
                       COUNT(s.id) AS calls
                FROM apis a
                LEFT JOIN api_stats s ON s.api_name = a.name
                GROUP BY a.name
                ORDER BY a.sort_order ASC, a.name ASC
                """
            ).fetchall()
            total_calls = conn.execute("SELECT COUNT(*) AS total FROM api_stats").fetchone()["total"]
            site = _clean_site_settings(_public_site_settings(conn))

        rows = [_clean_api_row(dict(row)) for row in apis]
        if not any(row["name"] == "douyin_parse" for row in rows):
            rows.insert(0, _builtin_presentation_row("douyin_parse"))
        categories = sorted({row["category"] for row in rows if row["category"]})
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "site": site,
                "summary": {
                    "total_apis": len(rows),
                    "enabled_apis": sum(1 for row in rows if row["enabled"]),
                    "total_calls": total_calls,
                    "today_calls": sum(row["calls"] for row in rows[:3]),
                },
                "categories": [
                    {"name": item, "count": sum(1 for row in rows if row["category"] == item)}
                    for item in categories
                ],
                "apis": rows,
            },
        }

    @app.get("/portal/site", include_in_schema=False)
    def portal_site() -> dict:
        with get_conn() as conn:
            site = _clean_site_settings(_public_site_settings(conn))
        return {"code": 200, "msg": "success", "data": site}

    @app.get("/portal/apis/{name}", include_in_schema=False)
    def portal_api_detail(name: str) -> dict:
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT name, path, title, description, category, method,
                       response_type, response_body, status_code, enabled, is_builtin
                FROM apis
                WHERE name = ?
                """,
                (name,),
            ).fetchone()
            site = _clean_site_settings(_public_site_settings(conn))
        if not row:
            if name in API_PRESENTATION:
                return {"code": 200, "msg": "success", "site": site, "data": _builtin_presentation_row(name)}
            raise HTTPException(status_code=404, detail="API documentation not found")
        return {"code": 200, "msg": "success", "site": site, "data": _clean_api_row(dict(row))}

    @app.get("/doc/{name}.html", include_in_schema=False)
    def api_doc(name: str) -> HTMLResponse:
        return _read_frontend_page("doc.html")

    @app.get("/doc-{name}.html", include_in_schema=False)
    def api_doc_legacy(name: str) -> HTMLResponse:
        return _read_frontend_page("doc.html")

    @app.get("/register", include_in_schema=False)
    def register_page() -> HTMLResponse:
        return _read_frontend_page("register.html")

    @app.post("/register/key", include_in_schema=False)
    def register_key(name: str = "self-registered user") -> dict:
        if settings.is_production and not settings.allow_self_register:
            raise HTTPException(status_code=403, detail="Self registration is disabled in production")

        clean_name = (name or "self-registered user").strip()[:64] or "self-registered user"
        key = "ak_" + secrets.token_urlsafe(24)
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO api_keys(key, name, enabled, quota_per_day, created_at)
                VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP)
                """,
                (key, clean_name, settings.self_register_quota_per_day),
            )
        return {
            "code": 200,
            "msg": "registered",
            "data": {"key": key, "name": clean_name, "quota_per_day": settings.self_register_quota_per_day},
        }

    @app.get("/health", include_in_schema=False)
    def health() -> dict:
        with get_conn() as conn:
            apis = conn.execute("SELECT COUNT(*) AS total FROM apis").fetchone()["total"]
            keys = conn.execute("SELECT COUNT(*) AS total FROM api_keys").fetchone()["total"]
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
            "database": "ok",
            "apis": apis,
            "api_keys": keys,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


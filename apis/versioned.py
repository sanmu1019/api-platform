from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.routing import APIRoute

from apis.demo.route import router as demo_router
from apis.freeapi.route import router as freeapi_router
from apis.ip.route import router as ip_router
from apis.phone.route import router as phone_router
from apis.spider.route import router as spider_router
from apis.time.route import router as time_router
from apis.tools.route import router as tools_router
from apis.word.route import router as word_router
from core.depends import verify_api_key

v1_router = APIRouter(tags=["v1"])


def _register_aliases(source: APIRouter) -> None:
    for route in source.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith("/api"):
            continue
        alias_path = "/api/v1" + route.path.removeprefix("/api")
        v1_router.add_api_route(
            alias_path,
            route.endpoint,
            methods=list(route.methods or ["GET"]),
            name=f"v1_{route.name}",
            dependencies=[Depends(verify_api_key)],
            response_model=None,
        )


for item in [demo_router, ip_router, time_router, phone_router, word_router, freeapi_router, tools_router, spider_router]:
    _register_aliases(item)


@v1_router.get("/api/version", include_in_schema=False)
def api_version() -> dict:
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "current": "v1",
            "legacy_prefix": "/api",
            "versioned_prefix": "/api/v1",
            "compatibility": "旧路径继续可用，新项目建议逐步使用 /api/v1",
        },
    }

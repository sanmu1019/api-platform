"""路由存在性判定。

数据库里的 `apis` 表是「登记过的接口」的账本，会随版本演进残留已经不存在的
条目（路由被删、但 `init_db()` 的 `INSERT ... ON CONFLICT` 只增不删）。
判断一条记录还有没有对应路由，是门户列表与后台巡检共用的逻辑 ——
放在这里是为了避免两处实现各自漂移。
"""

from __future__ import annotations

from typing import Any

# 自定义接口都挂在动态路由下，具体某条是否存在要查库，不在本判定的范围内
_DYNAMIC_SLUG_PATHS = ("/api/{slug}", "/api/custom/{slug}")


def _collect_api_routes(routes, paths: set[str], names: set[str]) -> None:
    """递归收集路由中的 /api path 与 name。

    Starlette >= 0.35 把 include_router 的子路由包成 _IncludedRouter
    （带 original_router 属性），不再展开成独立 Route。只做扁平遍历会
    漏掉所有业务路由，导致门户把内置接口全过滤掉。
    """
    for route in routes:
        inner = getattr(route, "original_router", None)
        if inner is not None and hasattr(inner, "routes"):
            _collect_api_routes(inner.routes, paths, names)
            continue
        path = getattr(route, "path", "") or ""
        if not path.startswith("/api"):
            continue
        paths.add(path)
        name = getattr(route, "name", "") or ""
        if name:
            names.add(name)


def api_route_index(app: Any) -> tuple[set[str], set[str]]:
    """收集应用里所有 /api 路由的 path 与 name。"""
    paths: set[str] = set()
    names: set[str] = set()
    _collect_api_routes(getattr(app, "routes", []) or [], paths, names)
    return paths, names


def route_exists(paths: set[str], names: set[str], name: str, path: str, is_builtin: bool) -> bool:
    """这条 `apis` 记录是否还有对应路由。

    内置接口必须精确匹配到路由；自定义接口走动态路由，只要动态路由还在就算
    存在（它本身是否被删是另一回事，由动态接口自己的查询负责）。
    """
    if path in paths or name in names:
        return True
    if not is_builtin:
        return any(slug in paths for slug in _DYNAMIC_SLUG_PATHS)
    return False

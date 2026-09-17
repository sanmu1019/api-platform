from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from core.depends import verify_api_key
from .service import DouyinParseError, parse_douyin, probe_douyin

router = APIRouter(prefix="/api/douyin", tags=["douyin"], dependencies=[Depends(verify_api_key)])


@router.api_route("/parse", methods=["GET", "POST"], name="douyin_parse")
def douyin_parse(
    url: str | None = Query(default=None, description="抖音分享链接或包含链接的文本"),
    debug: bool = Query(default=False, description="解析失败时返回页面诊断信息"),
    probe: bool = Query(default=False, description="只探测短链跳转和页面摘要，不强制解析视频数据"),
    timeout: float = Query(default=6.0, ge=2.0, le=20.0, description="服务端请求抖音的超时时间，秒"),
    payload: dict[str, Any] | None = Body(default=None),
) -> dict:
    text = url or ""
    if payload and isinstance(payload, dict):
        text = str(payload.get("url") or payload.get("text") or text)
        debug = bool(payload.get("debug", debug))
        probe = bool(payload.get("probe", probe))
        timeout = float(payload.get("timeout", timeout))

    if not text:
        raise HTTPException(status_code=400, detail="请提供 url 或 text")

    try:
        data = probe_douyin(text, timeout=timeout) if probe else parse_douyin(text, timeout=timeout, debug=debug)
    except DouyinParseError as exc:
        detail: dict[str, Any] = {"message": str(exc)}
        if debug or probe:
            detail["debug"] = exc.debug
        raise HTTPException(status_code=400, detail=detail) from exc

    return {
        "code": 200,
        "msg": "success",
        "data": data,
    }

from __future__ import annotations

import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.middleware import security_headers


logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "msg": exc.detail if isinstance(exc.detail, str) else "请求失败",
            "detail": exc.detail,
            "request_id": _request_id(request),
        },
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "msg": "请求参数校验失败",
            "detail": exc.errors(),
            "request_id": _request_id(request),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 500 对调用方只返回一句通用文案（不泄露内部细节），但服务端必须留下完整堆栈，
    # 否则线上出问题时无从查起。request_id 一并记录，方便和访问日志对齐。
    # 显式传 exc_info=exc（而不是 logger.exception）：后者依赖调用时存在"当前异常"，
    # 若处理器不是在 except 块内被调用，堆栈就会打印成 NoneType: None。
    request_id = _request_id(request)
    logger.error(
        "未处理异常 request_id=%s %s %s",
        request_id,
        request.method,
        request.url.path,
        exc_info=exc,
    )
    # 这个处理器由最外层的 ServerErrorMiddleware 调用，响应不会再经过
    # SecurityHeadersMiddleware 与 AccessLogMiddleware —— 所以加固头和
    # X-Request-ID 必须在这里自己补上，否则 500 是唯一"裸奔"的响应。
    headers = security_headers()
    if request_id:
        headers["X-Request-ID"] = request_id
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "msg": "服务器内部错误",
            "detail": "internal server error",
            "request_id": request_id,
        },
        headers=headers,
    )

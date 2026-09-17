from __future__ import annotations

import base64
import hashlib
import random
import secrets
import string
import time
import uuid
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query

from apis.data_loader import load_lines
from core.depends import verify_api_key

router = APIRouter(prefix="/api", tags=["tools"], dependencies=[Depends(verify_api_key)])


@router.get("/tool/timestamp", name="tool_timestamp")
def timestamp(value: int | None = None) -> dict:
    # 两个坑：
    # 1. 原来写的是 `value or time.time()`，value=0（1970 纪元，合法输入）
    #    是 falsy，会被当成"没传"而返回当前时间。
    # 2. datetime.fromtimestamp 对超范围值会抛异常，未捕获就是 500 —— 用户
    #    传个负数或超大数就能打出服务器内部错误。
    ts = int(time.time()) if value is None else int(value)
    try:
        dt = datetime.fromtimestamp(ts)
    except (OSError, OverflowError, ValueError):
        raise HTTPException(status_code=400, detail="timestamp 超出可表示范围") from None
    return {
        "code": 200,
        "msg": "success",
        "data": {"timestamp": ts, "datetime": dt.strftime("%Y-%m-%d %H:%M:%S")},
    }


@router.get("/tool/hash", name="tool_hash")
def hash_text(text: str = Query(...), algorithm: str = "md5") -> dict:
    algorithm = algorithm.lower()
    if algorithm not in {"md5", "sha1", "sha256", "sha512"}:
        raise HTTPException(status_code=400, detail="algorithm 仅支持 md5/sha1/sha256/sha512")
    digest = hashlib.new(algorithm)
    digest.update(text.encode("utf-8"))
    return {"code": 200, "msg": "success", "data": {"algorithm": algorithm, "text": text, "hash": digest.hexdigest()}}


@router.get("/tool/base64", name="tool_base64")
def base64_api(text: str = Query(...), mode: str = "encode") -> dict:
    mode = mode.lower()
    if mode == "encode":
        result = base64.b64encode(text.encode("utf-8")).decode()
    elif mode == "decode":
        try:
            result = base64.b64decode(text.encode()).decode("utf-8")
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Base64 解码失败") from exc
    else:
        raise HTTPException(status_code=400, detail="mode 仅支持 encode/decode")
    return {"code": 200, "msg": "success", "data": {"mode": mode, "input": text, "result": result}}


@router.get("/tool/uuid", name="tool_uuid")
def uuid_api(count: int = Query(1, ge=1, le=50)) -> dict:
    values = [str(uuid.uuid4()) for _ in range(count)]
    return {"code": 200, "msg": "success", "data": {"count": count, "items": values}}


@router.get("/tool/password", name="tool_password")
def password(length: int = Query(16, ge=6, le=64), symbols: bool = True) -> dict:
    alphabet = string.ascii_letters + string.digits
    if symbols:
        alphabet += "!@#$%^&*_-+="
    value = "".join(secrets.choice(alphabet) for _ in range(length))
    return {"code": 200, "msg": "success", "data": {"length": length, "password": value}}


@router.get("/tool/color", name="tool_color")
def color() -> dict:
    rgb = [random.randint(0, 255) for _ in range(3)]
    hex_value = "#{:02x}{:02x}{:02x}".format(*rgb)
    return {"code": 200, "msg": "success", "data": {"hex": hex_value, "rgb": rgb}}


@router.get("/tool/nickname", name="tool_nickname")
def nickname() -> dict:
    value = random.choice(load_lines("nickname_prefixes.txt")) + random.choice(load_lines("nickname_suffixes.txt")) + str(random.randint(10, 99))
    return {"code": 200, "msg": "success", "data": {"nickname": value}}


@router.get("/image/placeholder", name="image_placeholder")
def placeholder(width: int = Query(600, ge=1, le=3000), height: int = Query(400, ge=1, le=3000), text: str = "API") -> dict:
    url = f"https://placehold.co/{width}x{height}?text={quote(text)}"
    return {"code": 200, "msg": "success", "data": {"width": width, "height": height, "text": text, "url": url}}


@router.get("/image/qrcode", name="image_qrcode")
def qrcode(text: str = Query(..., min_length=1), size: int = Query(220, ge=80, le=800)) -> dict:
    # 空文本原来也返回 200，给出的是一个内容为空的二维码地址，扫出来什么都没有
    if not text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")
    url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={quote(text)}"
    return {"code": 200, "msg": "success", "data": {"text": text, "size": size, "url": url}}

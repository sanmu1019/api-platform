from __future__ import annotations

import base64
import hashlib
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key

router = APIRouter(prefix="/api", tags=["tools"], dependencies=[Depends(verify_api_key)])


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


@router.get("/image/qrcode", name="image_qrcode")
def qrcode(text: str = Query(..., min_length=1), size: int = Query(220, ge=80, le=800)) -> dict:
    # 空文本原来也返回 200，给出的是一个内容为空的二维码地址，扫出来什么都没有
    if not text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")
    url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={quote(text)}"
    return {"code": 200, "msg": "success", "data": {"text": text, "size": size, "url": url}}

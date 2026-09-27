from fastapi import APIRouter, Depends
import random

from apis.data_loader import load_lines
from core.depends import verify_api_key

public_router = APIRouter(prefix="/api", tags=["public"], dependencies=[Depends(verify_api_key)])


@public_router.get("/yiyan", name="yiyan_public")
def yiyan_public() -> dict:
    """随机一言。"""
    return {"code": 200, "msg": "success", "data": {"text": random.choice(load_lines("yiyan.txt"))}}

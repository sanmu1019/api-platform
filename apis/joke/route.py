from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from fastapi import APIRouter, Depends

from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/joke", tags=["joke"], dependencies=[Depends(verify_api_key)])

DATA_FILE = Path(__file__).parent / "jokes.json"
_jokes: list[dict] = []


def _load_jokes() -> list[dict]:
    global _jokes
    if not _jokes:
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                _jokes = json.load(f)
        except Exception as e:
            logger.error("加载段子数据失败: %s", e)
            _jokes = []
    return _jokes


@router.get("/random", name="joke_random")
def joke_random() -> dict:
    """随机获取一条段子。"""
    jokes = _load_jokes()
    if not jokes:
        return {"code": 500, "msg": "段子数据加载失败", "data": None}
    item = random.choice(jokes)
    return {
        "code": 200,
        "msg": "success",
        "data": item,
        "total": len(jokes),
    }

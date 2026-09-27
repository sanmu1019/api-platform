from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/joke", tags=["joke"], dependencies=[Depends(verify_api_key)])

DATA_FILE = Path(__file__).parent / "jokes.json"
RETRY_INTERVAL = 60  # 加载失败后至少间隔多少秒再重试
_jokes: list[dict] = []
_loaded = False
_last_attempt = 0.0


def _load_jokes() -> list[dict]:
    global _jokes, _loaded, _last_attempt
    if _loaded:
        return _jokes
    now = time.monotonic()
    if _last_attempt and now - _last_attempt < RETRY_INTERVAL:
        return _jokes
    _last_attempt = now
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            _jokes = json.load(f)
        _loaded = True
    except Exception as e:
        logger.error("加载段子数据失败: %s", e)
        _jokes = []
    return _jokes


@router.get("/random", name="joke_random")
def joke_random() -> dict:
    """随机获取一条段子。"""
    jokes = _load_jokes()
    if not jokes:
        raise HTTPException(status_code=503, detail="段子数据加载失败")
    item = random.choice(jokes)
    return {
        "code": 200,
        "msg": "success",
        "data": item,
        "total": len(jokes),
    }

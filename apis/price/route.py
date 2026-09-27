from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/price", tags=["price"], dependencies=[Depends(verify_api_key)])

TENCENT_URL = "https://qt.gtimg.cn/q="
TIMEOUT = 10
CACHE_TTL = 300  # 行情缓存 5 分钟

# 支持的品种：代码 -> (名称, 单位)
SYMBOLS = {
    "gold": ("hf_GC", "纽约黄金", "美元/盎司"),
    "silver": ("hf_SI", "纽约白银", "美元/盎司"),
    "oil": ("hf_CL", "纽约原油", "美元/桶"),
}

_cache: dict[str, tuple[float, Any]] = {}


def _parse_tencent(raw: str) -> dict | None:
    """解析腾讯财经行情字符串。"""
    m = re.search(r'v_\w+="([^"]+)"', raw)
    if not m:
        return None
    parts = m.group(1).split(",")
    if len(parts) < 14:
        return None
    try:
        return {
            "price": float(parts[0]),
            "change_pct": float(parts[1]),
            "open": float(parts[2]),
            "high": float(parts[4]),
            "low": float(parts[5]),
            "time": parts[6],
            "prev_close": float(parts[7]),
            "prev_settle": float(parts[8]),
            "date": parts[12],
            "name": parts[13],
        }
    except (ValueError, IndexError):
        return None


def _fetch_quotes(symbols: list[str]) -> dict[str, dict]:
    codes = ",".join(symbols)
    cache_key = f"tencent:{codes}"
    now = time.time()
    if cache_key in _cache:
        expire, data = _cache[cache_key]
        if now < expire:
            return data

    try:
        resp = requests.get(f"{TENCENT_URL}{codes}", timeout=TIMEOUT)
        resp.encoding = "gbk"
        resp.raise_for_status()
        result = {}
        for line in resp.text.strip().split(";"):
            line = line.strip()
            if not line:
                continue
            quote = _parse_tencent(line)
            if quote:
                result[quote["name"]] = quote
        _cache[cache_key] = (now + CACHE_TTL, result)
        return result
    except Exception as e:
        logger.warning("行情获取失败: %s", e)
        if cache_key in _cache:
            return _cache[cache_key][1]
        raise HTTPException(status_code=502, detail=f"行情获取失败: {e}")


@router.get("/gold", name="price_gold")
def price_gold() -> dict:
    """黄金行情（纽约黄金期货）。"""
    quotes = _fetch_quotes([SYMBOLS["gold"][0]])
    name = SYMBOLS["gold"][1]
    quote = quotes.get(name)
    if not quote:
        raise HTTPException(status_code=502, detail="黄金行情获取失败")
    quote["unit"] = SYMBOLS["gold"][2]
    return {"code": 200, "msg": "success", "data": quote, "source": "腾讯财经"}


@router.get("/silver", name="price_silver")
def price_silver() -> dict:
    """白银行情（纽约白银期货）。"""
    quotes = _fetch_quotes([SYMBOLS["silver"][0]])
    name = SYMBOLS["silver"][1]
    quote = quotes.get(name)
    if not quote:
        raise HTTPException(status_code=502, detail="白银行情获取失败")
    quote["unit"] = SYMBOLS["silver"][2]
    return {"code": 200, "msg": "success", "data": quote, "source": "腾讯财经"}


@router.get("/oil", name="price_oil")
def price_oil() -> dict:
    """原油行情（WTI 纽约原油）。"""
    quotes = _fetch_quotes([SYMBOLS["oil"][0]])
    name = SYMBOLS["oil"][1]
    quote = quotes.get(name)
    if not quote:
        raise HTTPException(status_code=502, detail="原油行情获取失败")
    quote["unit"] = SYMBOLS["oil"][2]
    return {"code": 200, "msg": "success", "data": quote, "source": "腾讯财经"}

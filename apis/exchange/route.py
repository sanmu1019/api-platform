from __future__ import annotations

import logging
import time
from typing import Any

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exchange", tags=["exchange"], dependencies=[Depends(verify_api_key)])

BASE_URL = "https://api.frankfurter.app"
TIMEOUT = 10
CACHE_TTL = 3600  # 汇率缓存 1 小时

_cache: dict[str, tuple[float, Any]] = {}


def _cached(key: str, fetcher):
    now = time.time()
    if key in _cache:
        expire, data = _cache[key]
        if now < expire:
            return data
    try:
        data = fetcher()
        _cache[key] = (now + CACHE_TTL, data)
        return data
    except Exception as e:
        logger.warning("汇率 %s 获取失败: %s", key, e)
        if key in _cache:
            return _cache[key][1]
        raise HTTPException(status_code=502, detail=f"汇率获取失败: {e}")


@router.get("/rate", name="exchange_rate")
def exchange_rate(
    from_currency: str = Query("USD", alias="from", min_length=3, max_length=3),
    to: str = Query("CNY", min_length=3, max_length=3),
    date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    """查询汇率。

    from: 源货币代码（默认 USD）
    to: 目标货币代码（默认 CNY）
    date: 可选，历史日期 YYYY-MM-DD，不传取最新
    """
    frm = from_currency.upper()
    to_upper = to.upper()
    cache_key = f"rate:{frm}:{to_upper}:{date or 'latest'}"

    def fetch():
        url = f"{BASE_URL}/{date or 'latest'}"
        params = {"from": frm, "to": to_upper}
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    data = _cached(cache_key, fetch)
    rates = data.get("rates", {})
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "from": frm,
            "to": to_upper,
            "rate": rates.get(to_upper),
            "date": data.get("date"),
            "amount": data.get("amount", 1),
        },
        "source": "European Central Bank",
    }


@router.get("/convert", name="exchange_convert")
def exchange_convert(
    from_currency: str = Query("USD", alias="from", min_length=3, max_length=3),
    to: str = Query("CNY", min_length=3, max_length=3),
    amount: float = Query(1.0, gt=0),
) -> dict:
    """货币转换。

    from: 源货币代码（默认 USD）
    to: 目标货币代码（默认 CNY）
    amount: 金额（默认 1）
    """
    frm = from_currency.upper()
    to_upper = to.upper()
    cache_key = f"rate:{frm}:{to_upper}:latest"

    def fetch():
        resp = requests.get(
            f"{BASE_URL}/latest",
            params={"from": frm, "to": to_upper},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    data = _cached(cache_key, fetch)
    rate = data.get("rates", {}).get(to_upper)
    if rate is None:
        raise HTTPException(status_code=400, detail=f"不支持的货币: {to_upper}")

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "from": frm,
            "to": to_upper,
            "amount": amount,
            "rate": rate,
            "result": round(amount * rate, 4),
            "date": data.get("date"),
        },
        "source": "European Central Bank",
    }

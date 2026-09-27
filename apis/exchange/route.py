from __future__ import annotations

import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key
from core.ttlcache import TTLCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exchange", tags=["exchange"], dependencies=[Depends(verify_api_key)])

BASE_URL = "https://api.frankfurter.app"
TIMEOUT = 10
CACHE_TTL = 3600  # 汇率缓存 1 小时

_cache = TTLCache(maxsize=512, ttl=CACHE_TTL)


def _cached(key: str, fetcher):
    data = _cache.get(key)
    if data is not None:
        return data
    try:
        data = fetcher()
    except HTTPException:
        raise
    except Exception:
        logger.exception("汇率 %s 获取失败", key)
        stale = _cache.get(key, allow_stale=True)
        if stale is not None:
            return stale
        raise HTTPException(status_code=502, detail="汇率获取失败")
    _cache.set(key, data)
    return data


@router.get("/rate", name="exchange_rate")
def exchange_rate(
    from_currency: str = Query("USD", alias="from", pattern="^[A-Za-z]{3}$"),
    to: str = Query("CNY", pattern="^[A-Za-z]{3}$"),
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
    rate = data.get("rates", {}).get(to_upper)
    if rate is None:
        raise HTTPException(status_code=400, detail=f"不支持的货币: {to_upper}")
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "from": frm,
            "to": to_upper,
            "rate": rate,
            "date": data.get("date"),
            "amount": data.get("amount", 1),
        },
        "source": "European Central Bank",
    }


@router.get("/convert", name="exchange_convert")
def exchange_convert(
    from_currency: str = Query("USD", alias="from", pattern="^[A-Za-z]{3}$"),
    to: str = Query("CNY", pattern="^[A-Za-z]{3}$"),
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

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/weather", tags=["weather"], dependencies=[Depends(verify_api_key)])

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
TIMEOUT = 10
CACHE_TTL = 600  # 天气缓存 10 分钟

_cache: dict[str, tuple[float, Any]] = {}

# WMO 天气代码映射
WEATHER_CODES = {
    0: "晴", 1: "大部晴", 2: "局部多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    56: "冻毛毛雨(小)", 57: "冻毛毛雨(大)",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨(小)", 67: "冻雨(大)",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}


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
        logger.warning("天气 %s 获取失败: %s", key, e)
        if key in _cache:
            return _cache[key][1]
        raise HTTPException(status_code=502, detail=f"天气获取失败: {e}")


def _weather_desc(code: int) -> str:
    return WEATHER_CODES.get(code, f"未知({code})")


def _geocode(city: str) -> dict:
    """根据城市名获取经纬度。"""
    resp = requests.get(
        GEO_URL,
        params={"name": city, "count": 1, "language": "zh", "format": "json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise HTTPException(status_code=404, detail=f"未找到城市: {city}")
    return results[0]


@router.get("/current", name="weather_current")
def weather_current(
    city: str = Query(..., min_length=1, max_length=50),
) -> dict:
    """实时天气。

    city: 城市名，如 北京、上海、南阳
    """
    cache_key = f"current:{city}"

    def fetch():
        geo = _geocode(city)
        resp = requests.get(
            FORECAST_URL,
            params={
                "latitude": geo["latitude"],
                "longitude": geo["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,pressure_msl",
                "timezone": "auto",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        data["_city_name"] = geo.get("name", city)
        data["_country"] = geo.get("country", "")
        data["_admin1"] = geo.get("admin1", "")
        return data

    data = _cached(cache_key, fetch)
    current = data.get("current", {})
    code = current.get("weather_code", 0)
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "city": data.get("_city_name", city),
            "region": data.get("_admin1", ""),
            "country": data.get("_country", ""),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "timezone": data.get("timezone"),
            "temperature": current.get("temperature_2m"),
            "apparent_temperature": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "weather": _weather_desc(code),
            "weather_code": code,
            "wind_speed": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
            "pressure": current.get("pressure_msl"),
            "time": current.get("time"),
            "units": {
                "temperature": "°C",
                "humidity": "%",
                "wind_speed": "km/h",
                "pressure": "hPa",
            },
        },
        "source": "Open-Meteo (CC BY 4.0)",
    }

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from core.config import settings
from core.depends import verify_api_key
from core.ttlcache import TTLCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hot", tags=["hot"], dependencies=[Depends(verify_api_key)])

CACHE_TTL = 300  # 5 分钟
# 内存缓存：platform -> data（键为固定平台名）
_cache = TTLCache(maxsize=32, ttl=CACHE_TTL)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
TIMEOUT = 10


def _proxies() -> dict[str, str] | None:
    """GitHub 等被墙站点复用抖音代理配置。"""
    proxy = getattr(settings, "douyin_proxy", None)
    if proxy:
        return {"http": proxy, "https": proxy}
    return None


def _cached(key: str, fetcher) -> tuple[Any, bool]:
    """返回 (data, hit)；hit 表示数据来自缓存（含上游失败时的旧缓存兜底）。"""
    data = _cache.get(key)
    if data is not None:
        return data, True
    try:
        data = fetcher()
    except HTTPException:
        raise
    except Exception:
        logger.exception("热榜 %s 抓取失败", key)
        # 失败时如果有旧缓存就用旧的
        stale = _cache.get(key, allow_stale=True)
        if stale is not None:
            return stale, True
        raise HTTPException(status_code=502, detail=f"{key} 热榜抓取失败")
    _cache.set(key, data)
    return data, False


def _fetch_weibo() -> list[dict]:
    resp = requests.get(
        "https://weibo.com/ajax/side/hotSearch",
        headers={"User-Agent": UA, "Referer": "https://weibo.com/"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    realtime = data.get("data", {}).get("realtime", [])
    return [
        {
            "rank": idx + 1,
            "title": item.get("word", ""),
            "hot": item.get("num", 0),
            "url": f"https://s.weibo.com/weibo?q=%23{item.get('word', '')}%23",
            "tag": item.get("label_name", ""),
        }
        for idx, item in enumerate(realtime)
    ]


def _fetch_baidu() -> list[dict]:
    resp = requests.get(
        "https://top.baidu.com/board?tab=realtime",
        headers={"User-Agent": UA},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    # 百度热搜数据嵌在页面的 <!--s-data:...--> 注释里
    match = re.search(r'<!--s-data:(.*?)-->', resp.text, re.DOTALL)
    if not match:
        raise ValueError("百度热搜数据未找到")
    data = json.loads(match.group(1))
    cards = data.get("data", {}).get("cards", [])
    content = []
    for card in cards:
        content.extend(card.get("content", []))
    return [
        {
            "rank": idx + 1,
            "title": item.get("word", ""),
            "hot": item.get("hotScore", ""),
            "url": item.get("url", ""),
            "desc": item.get("desc", "")[:100],
        }
        for idx, item in enumerate(content)
    ]


def _fetch_github() -> list[dict]:
    """GitHub Trending：国内直连超时，走代理（复用 douyin_proxy）。"""
    resp = requests.get(
        "https://github.com/trending",
        headers={"User-Agent": UA},
        timeout=TIMEOUT,
        proxies=_proxies(),
    )
    resp.raise_for_status()
    repos = re.findall(
        r'<h2[^>]*>\s*<a[^>]*href="(/[^"]+)"',
        resp.text, re.DOTALL,
    )
    desc_match = re.findall(
        r'<p class="col-9 color-fg-muted my-1 pr-4">\s*(.*?)\s*</p>',
        resp.text, re.DOTALL,
    )
    result = []
    for idx, href in enumerate(repos[:25]):
        name = href.lstrip("/")
        desc = desc_match[idx].strip() if idx < len(desc_match) else ""
        result.append({
            "rank": idx + 1,
            "title": name,
            "url": f"https://github.com{href}",
            "desc": re.sub(r'<[^>]+>', '', desc)[:150],
        })
    return result


def _fetch_bilibili() -> list[dict]:
    resp = requests.get(
        "https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1",
        headers={"User-Agent": UA, "Referer": "https://www.bilibili.com/"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", {}).get("list", [])
    return [
        {
            "rank": idx + 1,
            "title": item.get("title", ""),
            "up": item.get("owner", {}).get("name", ""),
            "play": item.get("stat", {}).get("view", 0),
            "url": f"https://www.bilibili.com/video/{item.get('bvid', '')}",
            "pic": item.get("pic", ""),
        }
        for idx, item in enumerate(items)
    ]


PLATFORMS = {
    "weibo": ("微博热搜", _fetch_weibo),
    "baidu": ("百度热搜", _fetch_baidu),
    "github": ("GitHub Trending", _fetch_github),
    "bilibili": ("B站热门", _fetch_bilibili),
}


@router.get("/{platform}", name="hot_list")
def hot_list(
    platform: str,
    limit: int = Query(20, ge=1, le=50),
) -> dict:
    """获取指定平台的热榜。

    platform 可选：weibo / baidu / github / bilibili
    数据缓存 5 分钟，避免频繁请求上游。
    GitHub 国内直连超时，需配置 douyin_proxy 代理。
    """
    if platform not in PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的平台: {platform}，可选: {', '.join(PLATFORMS.keys())}",
        )
    name, fetcher = PLATFORMS[platform]
    items, hit = _cached(platform, fetcher)
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "platform": platform,
            "name": name,
            "count": len(items[:limit]),
            "items": items[:limit],
            "cached": hit,
        },
    }

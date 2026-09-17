from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import urllib.parse
import urllib.request
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from apis.data_loader import load_lines
from core.depends import verify_api_key

router = APIRouter(prefix="/api", tags=["freeapi"], dependencies=[Depends(verify_api_key)])


@router.get("/yiyan", name="yiyan")
def yiyan() -> dict:
    """随机一言。"""
    return {"code": 200, "msg": "success", "data": {"text": random.choice(load_lines("yiyan.txt"))}}


@router.get("/avatar/random", name="avatar_random")
def avatar_random(seed: str | None = None, style: str = "adventurer") -> dict:
    """生成随机头像 URL，不在服务端下载图片。"""
    seed = seed or hashlib.md5(str(random.random()).encode()).hexdigest()[:10]
    safe_seed = urllib.parse.quote(seed)
    safe_style = re.sub(r"[^a-zA-Z0-9_-]", "", style) or "adventurer"
    url = f"https://api.dicebear.com/9.x/{safe_style}/svg?seed={safe_seed}"
    return {"code": 200, "msg": "success", "data": {"seed": seed, "style": safe_style, "url": url}}


@router.get("/short/hash", name="short_hash")
def short_hash(url: str = Query(..., description="需要生成短标识的 URL")) -> dict:
    """本地生成短链接标识，不做跳转存储，只返回短码。"""
    if not re.match(r"^https?://", url):
        raise HTTPException(status_code=400, detail="url 必须以 http:// 或 https:// 开头")
    code = base64.urlsafe_b64encode(hashlib.sha256(url.encode()).digest()).decode().rstrip("=")[:10]
    return {"code": 200, "msg": "success", "data": {"url": url, "short_code": code[:10]}}


@router.get("/bilibili/cover", name="bilibili_cover")
def bilibili_cover(bvid: str = Query(..., description="B站 BV 号")) -> dict:
    """抓取 B 站视频封面。

    原来这里不做任何请求，只是把上游 API 的 URL 拼成字符串返回，
    再附一句"如果需要服务端抓取封面，可后续扩展代理解析" —— 调用方拿到的
    不是封面，而是一段需要自己再去请求的地址，接口名不副实。
    """
    if not re.fullmatch(r"BV[0-9A-Za-z]{8,20}", bvid):
        raise HTTPException(status_code=400, detail="BV 号格式不正确")

    api = f"https://api.bilibili.com/x/web-interface/view?bvid={urllib.parse.quote(bvid)}"
    try:
        req = urllib.request.Request(
            api,
            headers={
                "User-Agent": "Mozilla/5.0",
                # B 站对无 Referer 的请求会更容易触发风控
                "Referer": "https://www.bilibili.com/",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"B 站接口请求失败：{type(exc).__name__}") from exc

    if payload.get("code") != 0:
        # 上游用 code 表达"稿件不存在/已删除"，别把它当成本地成功
        raise HTTPException(
            status_code=404,
            detail=f"未获取到视频信息：{payload.get('message') or 'unknown'}",
        )

    info = payload.get("data") or {}
    cover = info.get("pic") or ""
    if not cover:
        raise HTTPException(status_code=502, detail="上游返回中没有封面字段")

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "bvid": bvid,
            "title": info.get("title", ""),
            "cover": cover,
            "author": (info.get("owner") or {}).get("name", ""),
            "duration": info.get("duration", 0),
            "pubdate": info.get("pubdate", 0),
            "source": "bilibili",
        },
    }


@router.get("/bing/daily", name="bing_daily")
def bing_daily() -> dict:
    """必应每日图，失败时返回可用兜底图。"""
    api = "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN"
    fallback = {
        "title": "Bing Daily Image",
        "url": "https://www.bing.com/th?id=OHR.DefaultWallpaper_ZH-CN1920x1080.jpg",
        "copyright": "",
        "date": datetime.now().strftime("%Y%m%d"),
        "source": "fallback",
    }
    try:
        req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            import json

            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        image = data["images"][0]
        url = image["url"]
        if url.startswith("/"):
            url = "https://www.bing.com" + url
        result = {
            "title": image.get("title") or "Bing Daily Image",
            "url": url,
            "copyright": image.get("copyright", ""),
            "date": image.get("enddate", ""),
            "source": "bing",
        }
    except Exception:
        result = fallback
    return {"code": 200, "msg": "success", "data": result}

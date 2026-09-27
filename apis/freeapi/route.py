from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import urllib.parse
import urllib.request
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from apis.data_loader import load_lines
from core.depends import verify_api_key

router = APIRouter(prefix="/api", tags=["freeapi"], dependencies=[Depends(verify_api_key)])


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
def bilibili_cover(request: Request, bvid: str = Query(..., description="B站 BV 号")) -> dict:
    """抓取 B 站视频信息（标题、封面、作者、视频直链）。"""
    if not re.fullmatch(r"BV[0-9A-Za-z]{8,20}", bvid):
        raise HTTPException(status_code=400, detail="BV 号格式不正确")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/",
    }

    # 第一步：获取视频信息
    api = f"https://api.bilibili.com/x/web-interface/view?bvid={urllib.parse.quote(bvid)}"
    try:
        req = urllib.request.Request(api, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"B 站接口请求失败：{type(exc).__name__}") from exc

    if payload.get("code") != 0:
        raise HTTPException(
            status_code=404,
            detail=f"未获取到视频信息：{payload.get('message') or 'unknown'}",
        )

    info = payload.get("data") or {}
    cid = info.get("cid") or 0
    cover = info.get("pic") or ""

    # 第二步：获取视频播放地址（无登录默认 480P）
    video_url = ""
    audio_url = ""
    mp4_url = ""
    quality = 0
    if cid:
        play_api = (
            f"https://api.bilibili.com/x/player/playurl?"
            f"bvid={urllib.parse.quote(bvid)}&cid={cid}&qn=64&fnval=16&fourk=0"
        )
        try:
            req2 = urllib.request.Request(play_api, headers=headers)
            with urllib.request.urlopen(req2, timeout=8) as resp2:
                play_payload = json.loads(resp2.read().decode("utf-8", errors="replace"))
            if play_payload.get("code") == 0:
                play_data = play_payload.get("data") or {}
                quality = play_data.get("quality", 0)
                dash = play_data.get("dash") or {}
                videos = dash.get("video") or []
                audios = dash.get("audio") or []
                if videos:
                    video_url = videos[0].get("baseUrl") or videos[0].get("base_url") or ""
                if audios:
                    audio_url = audios[0].get("baseUrl") or audios[0].get("base_url") or ""
                if not video_url:
                    durl = play_data.get("durl") or []
                    if durl:
                        video_url = durl[0].get("url") or ""
        except Exception:
            pass

        # 第三步：获取合并好的 mp4 单文件直链
        mp4_api = (
            f"https://api.bilibili.com/x/player/playurl?"
            f"bvid={urllib.parse.quote(bvid)}&cid={cid}&qn=64&type=mp4"
        )
        try:
            req3 = urllib.request.Request(mp4_api, headers=headers)
            with urllib.request.urlopen(req3, timeout=8) as resp3:
                mp4_payload = json.loads(resp3.read().decode("utf-8", errors="replace"))
            if mp4_payload.get("code") == 0:
                durl = (mp4_payload.get("data") or {}).get("durl") or []
                if durl:
                    mp4_url = durl[0].get("url") or ""
        except Exception:
            pass

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
            "page_url": f"https://www.bilibili.com/video/{bvid}",
            "play_url": f"{request.base_url}api/bilibili/proxy?bvid={bvid}&type=mp4",
            "source": "bilibili",
        },
    }


_PASSTHROUGH_HEADERS = ("content-range", "content-length", "accept-ranges")


def _is_public_stream_url(url: str) -> bool:
    """视频流地址来自 B 站接口，会落到各种 PCDN 域名上，无法按域名白名单校验；只拒绝非 http(s) 与内网地址。"""
    from core.netsecurity import resolve_public_host

    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in ("http", "https") and resolve_public_host(parsed.hostname)[0]


@router.get("/bilibili/proxy", name="bilibili_proxy")
async def bilibili_proxy(
    request: Request,
    bvid: str = Query(..., description="B站 BV 号"),
    type_: str = Query("mp4", alias="type", pattern="^(mp4|dash)$", description="mp4 或 dash"),
) -> StreamingResponse:
    """代理 B 站视频流，自动带上 Referer 头，透传 Range 支持断点续传，浏览器可直接播放。"""
    if not re.fullmatch(r"BV[0-9A-Za-z]{8,20}", bvid):
        raise HTTPException(status_code=400, detail="BV 号格式不正确")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.bilibili.com/",
    }

    async with httpx.AsyncClient(timeout=8, headers=headers) as api_client:
        # 获取 cid
        api = f"https://api.bilibili.com/x/web-interface/view?bvid={urllib.parse.quote(bvid)}"
        try:
            resp = await api_client.get(api)
            payload = resp.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"获取视频信息失败：{exc.__class__.__name__}")

        cid = (payload.get("data") or {}).get("cid") or 0
        if not cid:
            raise HTTPException(status_code=404, detail="未找到视频")

        # 获取播放地址
        if type_ == "dash":
            play_api = (
                f"https://api.bilibili.com/x/player/playurl?"
                f"bvid={urllib.parse.quote(bvid)}&cid={cid}&qn=64&fnval=16&fourk=0"
            )
        else:
            play_api = (
                f"https://api.bilibili.com/x/player/playurl?"
                f"bvid={urllib.parse.quote(bvid)}&cid={cid}&qn=64&type=mp4"
            )

        try:
            resp2 = await api_client.get(play_api)
            play_payload = resp2.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"获取播放地址失败：{exc.__class__.__name__}")

    # 提取真实视频直链：主地址常落在 PCDN 节点上，连不上时依次换备用地址
    candidates: list[str] = []
    play_data = play_payload.get("data") or {}
    if type_ == "dash":
        dash = play_data.get("dash") or {}
        videos = dash.get("video") or []
        if videos:
            v = videos[0]
            candidates += [v.get("baseUrl") or v.get("base_url") or ""]
            candidates += v.get("backupUrl") or v.get("backup_url") or []
    durl = play_data.get("durl") or []
    if durl:
        candidates += [durl[0].get("url") or ""]
        candidates += durl[0].get("backup_url") or []
    candidates = [u for u in candidates if u]

    if not candidates:
        raise HTTPException(status_code=502, detail="未获取到视频流地址")
    candidates = [u for u in candidates if _is_public_stream_url(u)]
    if not candidates:
        raise HTTPException(status_code=502, detail="视频流地址不是公网地址")

    # 流式转发，透传客户端 Range
    upstream_headers = dict(headers)
    range_header = request.headers.get("range")
    if range_header:
        upstream_headers["Range"] = range_header

    client = httpx.AsyncClient(timeout=httpx.Timeout(30, connect=8), follow_redirects=False)
    upstream = None
    last_exc: Exception | None = None
    for real_url in candidates:
        try:
            upstream = await client.send(client.build_request("GET", real_url, headers=upstream_headers), stream=True)
            break
        except Exception as exc:
            last_exc = exc
    if upstream is None:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"视频流请求失败：{last_exc.__class__.__name__}")
    if upstream.status_code not in (200, 206):
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"视频流上游返回 {upstream.status_code}")

    async def iter_video():
        try:
            async for chunk in upstream.aiter_bytes(65536):
                yield chunk
        except Exception:
            return
        finally:
            await upstream.aclose()
            await client.aclose()

    out_headers = {"Content-Disposition": f'inline; filename="{bvid}.mp4"'}
    for name in _PASSTHROUGH_HEADERS:
        if name in upstream.headers:
            out_headers[name.title()] = upstream.headers[name]

    return StreamingResponse(
        iter_video(),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "video/mp4"),
        headers=out_headers,
    )


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

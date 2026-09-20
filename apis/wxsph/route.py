from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Query

from core.config import settings
from core.depends import verify_api_key

router = APIRouter(prefix="/api", tags=["wxsph"], dependencies=[Depends(verify_api_key)])

YUANBAO_PARSE_URL = "https://yuanbao.tencent.com/api/weixin/get_parse_result"
FEED_INFO_URL = "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# 缓存: share_url -> (expires_at, payload)
_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL = 600


def _get_cookie() -> str:
    """从 config.json 读取元宝 cookie。"""
    from core.config import settings
    cookie = settings.wxsph_cookie or os.environ.get("WXSPH_COOKIE", "")
    if not cookie:
        raise HTTPException(status_code=500, detail="未配置视频号解析 cookie，请在 config.json 中设置 wxsph_cookie")
    return cookie


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 15) -> dict:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"上游请求失败：{type(exc).__name__}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="上游返回非 JSON") from exc


def _parse_share_url(share_url: str, cookie: str) -> dict:
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://yuanbao.tencent.com",
        "Referer": "https://yuanbao.tencent.com/",
        "User-Agent": UA,
        "X-Requested-With": "XMLHttpRequest",
        "X-Source": "web",
        "Cookie": cookie,
    }
    payload = {"type": "video_channel_url", "url": share_url, "scene": 1}
    result = _post_json(YUANBAO_PARSE_URL, payload, headers)
    data = result.get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="解析失败：未获取到数据")
    if not data.get("playable_url") and not data.get("wx_export_id"):
        raise HTTPException(status_code=502, detail="解析失败：cookie 可能已过期")
    return data


def _split_playable(parse_data: dict) -> tuple[str, str]:
    playable_url = parse_data.get("playable_url") or ""
    token = ""
    export_id = ""
    if playable_url:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(playable_url).query)
        token = (qs.get("token") or [""])[0]
        export_id = (qs.get("eid") or [""])[0]
    export_id = export_id or parse_data.get("wx_export_id") or ""
    if not token or not export_id:
        raise HTTPException(status_code=502, detail="解析失败：缺少 token 或 export_id")
    return export_id, token


def _get_feed_info(export_id: str, token: str) -> dict:
    rid = f"{int(time.time()):x}-{os.urandom(4).hex()}"
    page_url = "https://channels.weixin.qq.com/finder-preview/pages/feed"
    url = f"{FEED_INFO_URL}?_rid={rid}&_pageUrl={urllib.parse.quote(page_url, safe='')}"
    referer = (
        f"{page_url}?entry_card_type=48&comment_scene=39&appid=0"
        f"&token={urllib.parse.quote(token, safe='')}&entry_scene=0&eid={urllib.parse.quote(export_id, safe='')}"
    )
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://channels.weixin.qq.com",
        "Referer": referer,
        "User-Agent": UA,
    }
    payload = {"baseReq": {"generalToken": token}, "exportId": export_id}
    result = _post_json(url, payload, headers)
    if result.get("errCode") not in (None, 0):
        raise HTTPException(status_code=502, detail=f"获取视频详情失败：errCode={result.get('errCode')}")
    return result


@router.get("/wxsph/parse", name="wxsph_parse")
def wxsph_parse(url: str = Query(..., description="视频号分享链接（https://weixin.qq.com/sph/...）")) -> dict:
    """解析微信视频号分享链接，返回视频直链和元信息。"""
    share_url = urllib.parse.unquote(url.strip())
    m = re.search(r"https?://[^\s\"'<>]+", share_url)
    if m:
        share_url = m.group(0).strip().strip("\"'")
    parsed = urllib.parse.urlparse(share_url)
    if parsed.netloc not in {"weixin.qq.com", "mp.weixin.qq.com"} or "/sph/" not in parsed.path:
        raise HTTPException(status_code=400, detail="只支持 https://weixin.qq.com/sph/... 格式的分享链接")

    # 缓存
    now = time.time()
    if share_url in _cache:
        exp, payload = _cache[share_url]
        if exp > now:
            return payload

    cookie = _get_cookie()
    parse_data = _parse_share_url(share_url, cookie)
    export_id, token = _split_playable(parse_data)
    feed = _get_feed_info(export_id, token)

    data = feed.get("data") or {}
    feed_info = data.get("feedInfo") or {}
    author = data.get("authorInfo") or {}

    # 提取视频直链
    video_url = ""
    for key in ("h264VideoInfo", "h265VideoInfo", "videoInfo"):
        item = feed_info.get(key) or {}
        if isinstance(item, dict) and (item.get("videoUrl") or item.get("url")):
            video_url = item.get("videoUrl") or item.get("url") or ""
            break
    if not video_url:
        video_url = feed_info.get("videoUrl") or ""

    title = feed_info.get("title") or feed_info.get("description") or parse_data.get("title") or ""
    cover = feed_info.get("coverUrl") or feed_info.get("cover_url") or ""

    result = {
        "code": 200,
        "msg": "success",
        "data": {
            "title": title,
            "cover": cover,
            "video_url": video_url,
            "author": author.get("nickname") or author.get("username") or "",
            "share_url": share_url,
            "source": "wechat_channels",
        },
    }
    _cache[share_url] = (now + CACHE_TTL, result)
    return result

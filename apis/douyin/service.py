"""抖音无水印解析。

只走官方详情接口（/aweme/v1/web/aweme/detail/），a_bogus 签名 + ttwid。
分享页不再内嵌作品数据（2026 年 8 月改版后 _ROUTER_DATA 只剩元数据），
所以页面解析的兜底层已移除。国内 IP 被风控时请配置 douyin_proxy。
"""

from __future__ import annotations

import html as html_lib
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html import unescape
from typing import Any

from . import detail_api
from core.config import settings


URL_RE = re.compile(r'https?://[^\s<>"]+?(?:douyin\.com|iesdouyin\.com)[^\s<>"]*')
AWEME_RE = re.compile(r"(?:video|note)/(\d+)")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)

USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
)


class DouyinParseError(RuntimeError):
    """抖音解析失败。"""

    def __init__(self, message: str, debug: dict[str, Any] | None = None):
        super().__init__(message)
        self.debug = debug or {}


@dataclass
class FetchResult:
    input_url: str
    final_url: str = ""
    html: str = ""
    status: int | None = None
    title: str = ""
    headers: dict[str, str] = field(default_factory=dict)


def extract_url(text: str) -> str:
    """从分享文本中提取第一个抖音 URL。"""
    match = URL_RE.search(text or "")
    if not match:
        raise DouyinParseError("未找到抖音链接", {"input": text})
    return match.group(0).rstrip("，。.!！?？、/")


def _title(html: str) -> str:
    match = TITLE_RE.search(html or "")
    if not match:
        return ""
    return re.sub(r"\s+", " ", unescape(match.group(1))).strip()


def _fetch(url: str, timeout: float = 6.0, max_bytes: int = 2_000_000) -> FetchResult:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "close",
        },
    )
    opener = None
    if settings.douyin_proxy:
        proxy_handler = urllib.request.ProxyHandler({
            "http": settings.douyin_proxy,
            "https": settings.douyin_proxy,
        })
        opener = urllib.request.build_opener(proxy_handler)
    try:
        ctx = opener.open(req, timeout=timeout) if opener else urllib.request.urlopen(req, timeout=timeout)
        with ctx as resp:
            final_url = resp.geturl()
            raw = resp.read(max_bytes)
            charset = resp.headers.get_content_charset() or "utf-8"
            html = raw.decode(charset, errors="replace")
            return FetchResult(
                input_url=url,
                final_url=final_url,
                html=html,
                status=getattr(resp, "status", None),
                title=_title(html),
                headers={k: v for k, v in resp.headers.items()},
            )
    except socket.timeout as exc:
        raise DouyinParseError("请求抖音页面超时", {"input_url": url, "timeout": timeout, "stage": "fetch"}) from exc
    except urllib.error.URLError as exc:
        raise DouyinParseError(f"请求抖音页面失败：{exc.reason}", {"input_url": url, "stage": "fetch"}) from exc
    except Exception as exc:  # pragma: no cover
        raise DouyinParseError(f"请求抖音页面失败：{exc}", {"input_url": url, "stage": "fetch"}) from exc


def _extract_aweme_id(url: str, html: str) -> str:
    for source in (url, html):
        match = AWEME_RE.search(source or "")
        if match:
            return match.group(1)
    return ""


def _decode_url(value: str) -> str:
    try:
        return html_lib.unescape(value.encode().decode("unicode_escape"))
    except Exception:
        return html_lib.unescape(value or "")


def _clean_text(value: Any) -> str:
    return "" if value is None else html_lib.unescape(str(value)).strip()


def _script_hints(html: str) -> dict[str, Any]:
    return {
        "html_size": len(html or ""),
        "title": _title(html),
    }


def _first_text(obj: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return _clean_text(value)
    return ""


def _first_url(value: Any) -> str:
    if isinstance(value, str) and value.startswith("http"):
        return _decode_url(value)
    if isinstance(value, list):
        for item in value:
            found = _first_url(item)
            if found:
                return found
    if isinstance(value, dict):
        for key in ("url_list", "uri", "url", "play_addr", "download_addr", "cover", "origin_cover"):
            if key in value:
                found = _first_url(value[key])
                if found:
                    return found
    return ""


def _pick_first_http_url(urls: list[Any]) -> str:
    for url in urls:
        if not isinstance(url, str) or not url:
            continue
        decoded = _decode_url(url)
        if decoded.startswith("http"):
            return decoded
    return ""


def _pick_video_url(urls: list[Any]) -> str:
    decoded_urls = [
        _decode_url(url).replace("playwm", "play")
        for url in urls
        if isinstance(url, str) and url
    ]
    snssdk_urls = [url for url in decoded_urls if "aweme.snssdk.com" in url]
    return snssdk_urls[0] if snssdk_urls else (decoded_urls[0] if decoded_urls else "")


def _pick_play_url(video: dict[str, Any]) -> str:
    """优先用 play_addr.uri 拼官方播放地址，最稳。"""
    play_addr = video.get("play_addr") if isinstance(video.get("play_addr"), dict) else {}
    play_uri = str(play_addr.get("uri") or "").strip()
    if play_uri:
        return f"https://aweme.snssdk.com/aweme/v1/play/?video_id={play_uri}&ratio=720p&line=0"
    video_url = _pick_video_url(play_addr.get("url_list") or [])
    if video_url:
        return video_url
    return _first_url(video.get("download_addr") or video)


def _is_playable_video(aweme: dict[str, Any]) -> bool:
    """图文作品的 video 是 duration=0 的配乐占位，要排除。"""
    video = aweme.get("video")
    if not isinstance(video, dict) or video.get("duration") == 0:
        return False
    return bool(_pick_play_url(video))


def _has_substantive_content(result: dict[str, Any]) -> bool:
    """没有实质内容就算失败，不返回空壳。"""
    if result.get("images"):
        return True
    return bool(result.get("video_url")) and result.get("kind") == "video"


def _is_plain_image_url(url: str) -> bool:
    clean = str(url or "").split("?", 1)[0].lower()
    return clean.endswith((".jpg", ".jpeg", ".png")) or "format=jpeg" in str(url).lower()


def _pick_preferred_cover_url(urls: list[Any]) -> tuple[str, str]:
    first_url = _pick_first_http_url(urls)
    for url in urls:
        if not isinstance(url, str) or not url:
            continue
        decoded = _decode_url(url)
        if decoded.startswith("http") and _is_plain_image_url(decoded):
            return decoded, first_url
    return "", first_url


def _pick_video_cover_url(video: dict[str, Any]) -> str:
    fallback = ""
    for key in ("cover", "origin_cover", "dynamic_cover", "animated_cover", "ai_dynamic_cover"):
        cover = video.get(key)
        if not isinstance(cover, dict):
            continue
        cover_url, first_url = _pick_preferred_cover_url(cover.get("url_list") or [])
        if cover_url:
            return cover_url
        fallback = fallback or first_url
        cover_url, first_url = _pick_preferred_cover_url([cover.get("uri"), cover.get("url")])
        if cover_url:
            return cover_url
        fallback = fallback or first_url
    return fallback


def _pick_image_url_groups(item: dict[str, Any]) -> list[list[str]]:
    groups: list[list[str]] = []
    seen_groups: set[tuple[str, ...]] = set()
    for image_info in item.get("images") or item.get("image_infos") or []:
        if not isinstance(image_info, dict):
            continue
        candidates: list[str] = []
        seen_urls: set[str] = set()
        for image_url in image_info.get("url_list") or []:
            if not isinstance(image_url, str) or not image_url.startswith("http"):
                continue
            decoded = html_lib.unescape(image_url)
            if decoded in seen_urls:
                continue
            candidates.append(decoded)
            seen_urls.add(decoded)
        key = tuple(candidates)
        if candidates and key not in seen_groups:
            groups.append(candidates)
            seen_groups.add(key)
    return groups


def _normalize_aweme(aweme: dict[str, Any], aweme_id: str, fetch: FetchResult, source_name: str) -> dict[str, Any]:
    author = aweme.get("author") if isinstance(aweme.get("author"), dict) else {}
    video = aweme.get("video") if isinstance(aweme.get("video"), dict) else {}
    music = aweme.get("music") if isinstance(aweme.get("music"), dict) else {}
    image_url_groups = _pick_image_url_groups(aweme)
    image_urls = [group[0] for group in image_url_groups if group]

    is_note = bool(image_urls)
    is_video = (not is_note) and _is_playable_video(aweme)
    video_url = _pick_play_url(video) if is_video else ""

    cover = _pick_video_cover_url(video) if (is_note or is_video) else ""
    title = _first_text(aweme, ("desc", "title")) or fetch.title

    kind = "note" if is_note else ("video" if is_video else "unknown")
    return {
        "input_url": fetch.input_url,
        "final_url": fetch.final_url,
        "aweme_id": str(aweme.get("aweme_id") or aweme_id or ""),
        "type": "images" if is_note else ("video" if is_video else "unknown"),
        "kind": kind,
        "title": title,
        "desc": title,
        "duration": video.get("duration") if is_video else None,
        "author": {
            "uid": author.get("uid") or author.get("sec_uid") or "",
            "nickname": _clean_text(author.get("nickname") or author.get("unique_id") or ""),
            "avatar": _first_url(author.get("avatar_thumb") or author.get("avatar_medium") or author.get("avatar_larger")),
        },
        "cover": cover,
        "video_url": video_url,
        "url": video_url,
        "images": image_urls,
        "image_url_groups": image_url_groups,
        "music": {
            "title": _clean_text(music.get("title") or ""),
            "author": _clean_text(music.get("author") or ""),
            "url": _first_url(music.get("play_url") or music),
        },
        "source": source_name,
        "raw_available": bool(aweme),
    }


def probe_douyin(text_or_url: str, timeout: float = 5.0) -> dict[str, Any]:
    """只做链接提取和页面探测 + 详情接口尝试，用于 debug。"""
    input_url = extract_url(text_or_url)
    fetch = _fetch(input_url, timeout=timeout, max_bytes=500_000)
    aweme_id = _extract_aweme_id(fetch.final_url, fetch.html)
    item_id = detail_api.extract_item_id(fetch.final_url) or aweme_id

    aweme = None
    detail_failure = ""
    if item_id:
        aweme, detail_failure = detail_api.fetch_aweme_detail(item_id, timeout=timeout)

    normalized = _normalize_aweme(aweme, aweme_id, fetch, "detail_api") if aweme else {}

    return {
        "input_url": input_url,
        "final_url": fetch.final_url,
        "status": fetch.status,
        "title": fetch.title,
        "aweme_id": aweme_id,
        "source": "detail_api" if aweme else "",
        "raw_available": bool(aweme),
        "has_content": bool(normalized.get("images") or normalized.get("video_url")),
        "kind": normalized.get("kind", "unknown"),
        "detail_failure": detail_failure,
        "hints": _script_hints(fetch.html),
    }


def _with_debug(
    result: dict[str, Any],
    fetch: FetchResult,
    detail_failure: str,
) -> dict[str, Any]:
    result["debug"] = {
        "fetch": {
            "status": fetch.status,
            "title": fetch.title,
            "html_size": len(fetch.html),
            "final_url": fetch.final_url,
        },
        "hints": _script_hints(fetch.html),
        "data_source": result.get("source", ""),
        "detail_api_failure": detail_failure,
        "proxy": settings.douyin_proxy or "direct (no proxy)",
    }
    return result


def parse_douyin(text_or_url: str, timeout: float = 6.0, debug: bool = False) -> dict[str, Any]:
    """解析抖音分享文本或 URL。

    走官方详情接口（a_bogus 签名 + ttwid）。国内 IP 被风控返回 403 时，
    请在 config.json 中配置 douyin_proxy（如 http://127.0.0.1:7890）后重试。
    """
    input_url = extract_url(text_or_url)
    fetch = _fetch(input_url, timeout=timeout)
    aweme_id = _extract_aweme_id(fetch.final_url, fetch.html)

    detail_failure = ""
    item_id = detail_api.extract_item_id(fetch.final_url) or aweme_id
    if not item_id:
        raise DouyinParseError(
            "未能从链接中提取作品 ID",
            {"input_url": input_url, "final_url": fetch.final_url, "status": fetch.status},
        )

    aweme, detail_failure = detail_api.fetch_aweme_detail(item_id, timeout=timeout)
    if not aweme:
        raise DouyinParseError(
            "抖音详情接口未返回数据，可能触发风控或签名失效"
            + ("；国内网络请配置 douyin_proxy 后重试" if not settings.douyin_proxy else f"（代理：{settings.douyin_proxy}）")
            + (f"：{detail_failure}" if detail_failure else ""),
            {
                "input_url": input_url,
                "final_url": fetch.final_url,
                "status": fetch.status,
                "title": fetch.title,
                "aweme_id": aweme_id,
                "detail_failure": detail_failure,
                "proxy": settings.douyin_proxy or "direct (no proxy)",
            },
        )

    result = _normalize_aweme(aweme, item_id, fetch, "detail_api")
    if not _has_substantive_content(result):
        raise DouyinParseError(
            "详情接口返回了作品壳但无实质内容（视频/图文数据缺失）",
            {"input_url": input_url, "aweme_id": item_id, "kind": result.get("kind")},
        )

    return _with_debug(result, fetch, detail_failure) if debug else result

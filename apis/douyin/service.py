from __future__ import annotations

import html as html_lib
import json
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from html import unescape
from typing import Any

from . import detail_api


URL_RE = re.compile(r'https?://[^\s<>"]+?(?:douyin\.com|iesdouyin\.com)[^\s<>"]*')
AWEME_RE = re.compile(r"(?:video|note)/(\d+)")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
ROUTER_DATA_RE = re.compile(r"window\._ROUTER_DATA\s*=\s*({.*?})\s*</script>", re.S)

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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
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


def _json_loads_loose(text: str) -> Any:
    text = unescape(text)
    text = urllib.parse.unquote(text)
    return json.loads(text)


def _find_render_data(html: str) -> tuple[Any | None, str]:
    patterns = [
        ("RENDER_DATA", r'<script id="RENDER_DATA" type="application/json">(.*?)</script>'),
        ("__NEXT_DATA__", r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'),
        ("_ROUTER_DATA", r"window\._ROUTER_DATA\s*=\s*(\{.*?\})</script>"),
    ]
    for name, pattern in patterns:
        match = re.search(pattern, html, re.S)
        if not match:
            continue
        try:
            return _json_loads_loose(match.group(1)), name
        except Exception:
            continue
    return None, ""


def _decode_url(value: str) -> str:
    try:
        return html_lib.unescape(value.encode().decode("unicode_escape"))
    except Exception:
        return html_lib.unescape(value or "")


def _clean_text(value: Any) -> str:
    return "" if value is None else html_lib.unescape(str(value)).strip()


def _script_hints(html: str) -> dict[str, Any]:
    keys = ("RENDER_DATA", "__NEXT_DATA__", "_ROUTER_DATA", "aweme_id", "video", "captcha", "verify")
    return {
        "html_size": len(html or ""),
        "title": _title(html),
        "contains": {key: key in (html or "") for key in keys},
    }


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


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


def _extract_router_aweme_item(html: str) -> dict[str, Any]:
    """按 DouyinParser 思路优先解析 window._ROUTER_DATA。"""
    match = ROUTER_DATA_RE.search(html or "")
    if not match:
        return {}
    try:
        router_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}

    loader_data = router_data.get("loaderData")
    if not isinstance(loader_data, dict):
        return {}

    for page_data in loader_data.values():
        if not isinstance(page_data, dict):
            continue
        video_info = page_data.get("videoInfoRes")
        if not isinstance(video_info, dict):
            continue
        item_list = video_info.get("item_list")
        if isinstance(item_list, list) and item_list and isinstance(item_list[0], dict):
            return item_list[0]
    return {}


def _pick_aweme(data: Any) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for obj in _walk(data):
        if any(key in obj for key in ("aweme_id", "desc", "video", "images", "image_infos")):
            score = 0
            score += 3 if obj.get("aweme_id") else 0
            score += 3 if obj.get("video") else 0
            score += 2 if obj.get("images") or obj.get("image_infos") else 0
            score += 1 if obj.get("desc") else 0
            candidates.append({"score": score, "obj": obj})
    if not candidates:
        return {}
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[0]["obj"]


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
    """按上游 DouyinParser 的做法，优先用 `play_addr.uri` 拼官方播放地址。

    `url_list` 里的地址多是带水印的 `playwm` 或短时效 CDN 链接，而
    `video_id=<uri>` 是官方播放接口，最稳。上游只在详情接口那条路这么做，
    这里统一用 —— 因为只有"已确认是视频"时才会走到这个函数。
    """
    play_addr = video.get("play_addr") if isinstance(video.get("play_addr"), dict) else {}
    play_uri = str(play_addr.get("uri") or "").strip()
    if play_uri:
        return f"https://aweme.snssdk.com/aweme/v1/play/?video_id={play_uri}&ratio=720p&line=0"
    video_url = _pick_video_url(play_addr.get("url_list") or [])
    if video_url:
        return video_url
    return _first_url(video.get("download_addr") or video)


def _is_playable_video(aweme: dict[str, Any]) -> bool:
    """是否为「真正的视频作品」。

    抖音**图文作品**的 `video` 字段是个占位：`duration == 0`，`play_addr`
    指向配乐（形如 `.../play/?video_id=music.mp3`）。上游 DouyinParser 的
    `_parse_video_item` 靠 `duration == 0` 把它排除掉，本地移植时漏了这一步，
    于是图文会被判成视频、视频地址指向一个 mp3。
    """
    video = aweme.get("video")
    if not isinstance(video, dict) or video.get("duration") == 0:
        return False
    return bool(_pick_play_url(video))


def _has_substantive_content(result: dict[str, Any]) -> bool:
    """这次解析是否真的拿到了作品内容。

    上游 DouyinParser 的原则是「没有实质内容就算失败」：`_parse_page_html`
    与 `_parse_via_detail_api` 在 note / video 都解析不出来时抛
    `VideoParserError`。本地移植时把这条丢了，于是「页面拿到了、但没识别出
    作品」会返回 `code=200` + 空壳数据，调用方无法区分成功与失败。
    """
    if result.get("images"):
        return True
    return bool(result.get("video_url")) and result.get("kind") == "video"


_LEGACY_PLAY_ADDR_RE = re.compile(
    r'"play_addr":\s*\{\s*"uri":\s*"[^"]*",\s*"url_list":\s*\[([^\]]*)\]'
)


def _match_json_string(text: str, key: str) -> str:
    match = re.search(rf'"{re.escape(key)}":\s*"([^"]*)"', text or "")
    if not match:
        return ""
    return _clean_text(_decode_url(match.group(1)))


def _extract_legacy_video(html: str) -> dict[str, Any]:
    """从裸 HTML 里正则捞 play_addr，作为最后一层兜底。

    上游 DouyinParser 有这一层（`_parse_legacy_video`）。2026 年 8 月分享页
    改版后 `_ROUTER_DATA` 不再稳定存在，这种「不看结构、只扫特征串」的兜底
    反而可能是唯一还能用的路。刻意不写 `duration`：留空即不触发
    `_is_playable_video` 里 `duration == 0` 的图文排除，因为这里已经先确认
    拿到了非空的视频地址。
    """
    match = _LEGACY_PLAY_ADDR_RE.search(html or "")
    if not match:
        return {}
    urls = [url.strip().strip('"') for url in match.group(1).split(",")]
    if not _pick_video_url(urls):
        return {}

    # 存原始 url_list 而不是已解码的单条地址：`_pick_play_url` 会自己再解一遍，
    # 避免对同一个串做两次 unicode_escape 解码。
    video: dict[str, Any] = {"play_addr": {"url_list": urls}}
    cover_match = re.search(r'"cover":\s*\{\s*"url_list":\s*\[\s*"([^"]+)"', html or "")
    if cover_match:
        video["cover"] = {"url_list": [_decode_url(cover_match.group(1))]}

    return {
        "desc": _match_json_string(html, "desc"),
        "author": {"nickname": _match_json_string(html, "nickname")},
        "video": video,
    }


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

    play_addr = video.get("play_addr") if isinstance(video.get("play_addr"), dict) else {}

    # 图文优先，且「是不是图文」只能以 images 为准 —— 上游 `_parse_page_html`
    # 就是先试 note 再试 video。抖音图文作品的 video 是 duration=0 的配乐占位，
    # 只看「有没有 video_url」会把图文判成视频（见 `_is_playable_video`）。
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
    """只做链接提取和页面探测，用于 debug，不强制解析成功。"""
    input_url = extract_url(text_or_url)
    fetch = _fetch(input_url, timeout=timeout, max_bytes=500_000)
    aweme_id = _extract_aweme_id(fetch.final_url, fetch.html)
    data, source_name = _find_render_data(fetch.html)
    router_item = _extract_router_aweme_item(fetch.html)
    aweme = router_item or (_pick_aweme(data) if data is not None else {})
    probe_source = "_ROUTER_DATA" if router_item else source_name

    normalized = _normalize_aweme(aweme, aweme_id, fetch, probe_source) if aweme else {}
    if not normalized:
        legacy = _extract_legacy_video(fetch.html)
        if legacy:
            normalized = _normalize_aweme(legacy, aweme_id, fetch, "_legacy_regex")

    return {
        "input_url": input_url,
        "final_url": fetch.final_url,
        "status": fetch.status,
        "title": fetch.title,
        "aweme_id": aweme.get("aweme_id") or aweme_id or "",
        "source": probe_source or (normalized.get("source", "") if normalized else ""),
        "raw_available": bool(aweme),
        "has_content": bool(normalized.get("images") or normalized.get("video_url")),
        "kind": normalized.get("kind", "unknown"),
        "hints": _script_hints(fetch.html),
    }


def _with_debug(
    result: dict[str, Any],
    fetch: FetchResult,
    detail_failure: str,
    attempts: list[str],
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
        "attempts": attempts,
    }
    return result


def parse_douyin(text_or_url: str, timeout: float = 6.0, debug: bool = False) -> dict[str, Any]:
    """解析抖音分享文本或 URL。

    四条路，按可靠性从高到低依次尝试，**每条路都必须产出实质内容才算成功**：

    1. 短链跳转拿到作品 ID -> 官方 `/aweme/v1/web/aweme/detail/` 接口
       （a_bogus 签名 + ttwid），从 wxbot 的 DouyinParser 移植而来。
    2. 分享页 `window._ROUTER_DATA`。
    3. 分享页 `RENDER_DATA` / `__NEXT_DATA__`。
    4. 裸 HTML 正则扫 `play_addr`（上游 `_parse_legacy_video` 那一层）。

    为什么要四层：HTML 那条路原本是唯一实现，但分享页在 2026 年 8 月改版后
    `_ROUTER_DATA` 不再稳定存在，线上表现为"页面已获取，但没有识别到视频/图文
    数据"。而官方接口依赖逆向签名，一旦抖音换算法也会全线失效。多层兜底不是
    为了"总有一条能中"，而是因为这几条的失效原因彼此独立。

    **关键**：`_normalize_aweme` 一定会返回一个 dict，但"返回了 dict"不等于
    "解析成功"。上游 DouyinParser 在 note / video 都解析不出来时直接抛错，
    本地移植时丢了这条判定，于是空壳会被当成 `code=200 msg=success` 返回 ——
    调用方拿到 `aweme_id` 和页面标题，却没有任何作品数据。这里用
    `_has_substantive_content` 把判定补回来。
    """
    input_url = extract_url(text_or_url)
    fetch = _fetch(input_url, timeout=timeout)
    aweme_id = _extract_aweme_id(fetch.final_url, fetch.html)

    attempts: list[str] = []
    detail_failure = ""

    def accept(result: dict[str, Any]) -> dict[str, Any] | None:
        if not _has_substantive_content(result):
            return None
        return _with_debug(result, fetch, detail_failure, attempts) if debug else result

    # 路 1：官方详情接口
    item_id = detail_api.extract_item_id(fetch.final_url) or aweme_id
    if item_id:
        aweme, detail_failure = detail_api.fetch_aweme_detail(item_id, timeout=timeout)
        if aweme:
            accepted = accept(_normalize_aweme(aweme, item_id, fetch, "detail_api"))
            if accepted:
                return accepted
            detail_failure = detail_failure or "详情接口返回了作品壳但无实质内容"
        attempts.append(f"detail_api: {detail_failure or '未返回作品数据'}")

    # 路 2：分享页 _ROUTER_DATA
    router_item = _extract_router_aweme_item(fetch.html)
    if router_item:
        accepted = accept(_normalize_aweme(router_item, aweme_id, fetch, "_ROUTER_DATA"))
        if accepted:
            return accepted
        attempts.append("_ROUTER_DATA: 作品数据无实质内容")
    else:
        attempts.append("_ROUTER_DATA: 页面中不存在")

    # 路 3：RENDER_DATA / __NEXT_DATA__
    data, source_name = _find_render_data(fetch.html)
    if data is not None:
        accepted = accept(
            _normalize_aweme(_pick_aweme(data), aweme_id, fetch, source_name or "render_data")
        )
        if accepted:
            return accepted
        attempts.append(f"页面数据({source_name}): 未识别出作品数据")
    else:
        attempts.append("页面数据(RENDER_DATA/__NEXT_DATA__): 页面中不存在")

    # 路 4：裸 HTML 正则兜底
    legacy = _extract_legacy_video(fetch.html)
    if legacy:
        accepted = accept(_normalize_aweme(legacy, aweme_id, fetch, "_legacy_regex"))
        if accepted:
            return accepted
        attempts.append("_legacy_regex: 未匹配到可用 play_addr")
    else:
        attempts.append("_legacy_regex: 页面中未找到 play_addr")

    raise DouyinParseError(
        "官方接口与页面解析都没拿到视频/图文数据，可能触发风控、链接失效或签名失效"
        + (f"（详情接口：{detail_failure}）" if detail_failure else ""),
        {
            "input_url": input_url,
            "final_url": fetch.final_url,
            "status": fetch.status,
            "title": fetch.title,
            "aweme_id": aweme_id,
            "attempts": attempts,
            "hints": _script_hints(fetch.html),
        },
    )

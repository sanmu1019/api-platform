import re
import json
from urllib.parse import urlparse, urljoin
import fake_useragent
from ..utils import create_async_client, validate_allowed_url
from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo
from core.config import settings


# 小红书官方域名白名单（精确域或其子域才允许访问）
_XHS_ALLOWED_DOMAINS = {"xiaohongshu.com", "xhslink.com", "xhslink.cn"}
# 只有主域才携带用户 Cookie，短链跳转阶段不带
_XHS_COOKIE_DOMAIN = "xiaohongshu.com"
_REDIRECT_STATUS = {301, 302, 303, 307, 308}


def _xhs_host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _is_allowed_xhs_url(url: str) -> bool:
    host = _xhs_host(url)
    return any(host == d or host.endswith("." + d) for d in _XHS_ALLOWED_DOMAINS)


class RedBook(BaseParser):
    """
    小红书
    """
    XHS_STATE_RE = re.compile(
        r"window\.__INITIAL_STATE__=(.*?)</script>",
        re.IGNORECASE | re.DOTALL,
    )

    def _get_headers(self, ios: bool = False, with_cookie: bool = True) -> dict:
        if ios:
            headers = {
                "User-Agent": fake_useragent.UserAgent(os=["ios"]).random,
                "Origin": "https://www.xiaohongshu.com",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.xiaohongshu.com/",
            }
        else:
            headers = {
                "User-Agent": fake_useragent.UserAgent(os=["windows"]).random,
                "Referer": "https://www.xiaohongshu.com/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        # Cookie 只在访问小红书主域时由 _safe_get 逐跳决定是否附加
        if with_cookie:
            cookie = getattr(settings, "xiaohongshu_cookie", "")
            if cookie:
                headers["_XHS_COOKIE"] = cookie
        return headers

    async def _safe_get(self, client, url: str, headers: dict, max_redirects: int = 5):
        """手动逐跳跟随重定向，每一跳都校验目标域名；Cookie 只发给小红书主域。"""
        cookie = headers.pop("_XHS_COOKIE", "")
        current = url
        for _ in range(max_redirects + 1):
            validate_allowed_url(current, tuple(_XHS_ALLOWED_DOMAINS))
            hop_headers = dict(headers)
            host = _xhs_host(current)
            if cookie and (host == _XHS_COOKIE_DOMAIN or host.endswith("." + _XHS_COOKIE_DOMAIN)):
                hop_headers["Cookie"] = cookie
            response = await client.get(current, headers=hop_headers, follow_redirects=False)
            if response.status_code in _REDIRECT_STATUS:
                location = response.headers.get("location")
                if not location:
                    return response
                current = urljoin(current, location)
                continue
            return response
        raise ValueError("重定向次数过多")

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        # 先尝试explore格式，失败了fallback到discovery
        try:
            return await self._parse_explore(share_url)
        except Exception:
            return await self._parse_discovery(share_url)

    async def _parse_explore(self, url: str) -> VideoInfo:
        headers = self._get_headers(ios=False)
        async with create_async_client() as client:
            response = await self._safe_get(client, url, headers)
            response.raise_for_status()
            html = response.text

        match = self.XHS_STATE_RE.search(html)
        if not match:
            raise ValueError("parse video json info from html fail")

        raw = match.group(1).replace("undefined", "null")
        state = json.loads(raw)

        note = self._find_xiaohongshu_note(state)
        if not note:
            raise ValueError("未找到小红书笔记内容")

        return self._build_video_info(note)

    async def _parse_discovery(self, url: str) -> VideoInfo:
        headers = self._get_headers(ios=True)
        async with create_async_client() as client:
            response = await self._safe_get(client, url, headers)
            response.raise_for_status()
            html = response.text

        match = self.XHS_STATE_RE.search(html)
        if not match:
            raise ValueError("parse video json info from html fail")

        raw = match.group(1).replace("undefined", "null")
        state = json.loads(raw)

        note = self._find_xiaohongshu_note(state)
        if not note:
            raise ValueError("未找到小红书笔记内容")

        return self._build_video_info(note)

    def _build_video_info(self, note: dict) -> VideoInfo:
        user = note.get("user") if isinstance(note.get("user"), dict) else {}
        images = self._xiaohongshu_images(note)

        video_url = ""
        h264_data = (
            note.get("video", {}).get("media", {}).get("stream", {}).get("h264", [])
        )
        if len(h264_data) > 0:
            video_url = h264_data[0].get("masterUrl", "")

        cover_url = ""
        if images:
            cover_url = images[0].url
        elif video_url:
            cover_url = h264_data[0].get("coverUrl", "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=note.get("title", ""),
            images=images,
            author=VideoAuthor(
                uid=user.get("userId", ""),
                name=user.get("nickname", "") or user.get("nickName", ""),
                avatar=user.get("avatar", ""),
            ),
        )

    def _find_xiaohongshu_note(self, state):
        if not isinstance(state, dict):
            return None
        note = state.get("note") if isinstance(state.get("note"), dict) else {}
        detail_map = note.get("noteDetailMap") if isinstance(note.get("noteDetailMap"), dict) else {}
        for wrapper in detail_map.values():
            if not isinstance(wrapper, dict):
                continue
            item = wrapper.get("note") if isinstance(wrapper.get("note"), dict) else wrapper
            if isinstance(item, dict) and (item.get("title") is not None or item.get("desc") is not None):
                return item
        return self._find_mapping(
            state,
            lambda item: bool(
                (item.get("title") is not None or item.get("desc") is not None)
                and ("imageList" in item or "image_list" in item or "video" in item)
                and ("user" in item or "userInfo" in item)
            ),
        )

    def _find_mapping(self, value, predicate):
        if isinstance(value, dict):
            if predicate(value):
                return value
            for item in value.values():
                found = self._find_mapping(item, predicate)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = self._find_mapping(item, predicate)
                if found:
                    return found
        return None

    def _xiaohongshu_images(self, note: dict) -> list[ImgInfo]:
        images = []
        for item in note.get("imageList") or note.get("image_list") or []:
            if not isinstance(item, dict):
                continue
            infos = item.get("infoList") or item.get("info_list") or []
            if isinstance(infos, list):
                for info in reversed(infos):
                    if isinstance(info, dict) and info.get("url"):
                        images.append(ImgInfo(url=info.get("url")))
                        break
            if not infos:
                url = item.get("url") or item.get("urlDefault")
                if url:
                    images.append(ImgInfo(url=url))
        return images

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("小红书暂不支持直接解析视频ID")

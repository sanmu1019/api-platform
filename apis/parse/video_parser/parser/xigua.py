import re
import json
import fake_useragent
from ..utils import create_async_client, safe_get
from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class XiGua(BaseParser):
    """
    西瓜视频
    """
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        async with create_async_client(follow_redirects=False) as client:
            response = await safe_get(
                client,
                share_url,
                ("ixigua.com",),
                headers={
                    "User-Agent": fake_useragent.UserAgent(os="iOS").random,
                    "Referer": "https://www.ixigua.com/",
                },
            )
            response.raise_for_status()
            html = response.text

        # 找视频数据
        match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(.*?)</script>", html, re.DOTALL)
        if not match:
            raise ValueError("parse video json info from html fail")

        raw = match.group(1).replace("undefined", "null")
        state = json.loads(raw)

        # 找视频信息
        video_info_data = self._find_video_data(state)
        if not video_info_data:
            raise ValueError("未找到西瓜视频内容")

        video_url = video_info_data.get("video_url", "")
        cover_url = video_info_data.get("cover", "")
        title = video_info_data.get("title", "")
        author_name = video_info_data.get("author", {}).get("name", "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(
                name=author_name,
            ),
        )

    def _find_video_data(self, state):
        if not isinstance(state, dict):
            return None
        # 递归查找视频数据
        return self._find_mapping(
            state,
            lambda item: bool(
                "video_url" in item and ("title" in item or "cover" in item)
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

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("西瓜视频暂不支持直接解析视频ID")

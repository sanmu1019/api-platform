import re
import json
import fake_useragent
from ..utils import create_async_client, safe_get
from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class AcFun(BaseParser):
    """
    AcFun
    """
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        async with create_async_client(follow_redirects=False) as client:
            response = await safe_get(
                client,
                share_url,
                ("acfun.cn",),
                headers={
                    "User-Agent": fake_useragent.UserAgent(os="iOS").random,
                    "Referer": "https://www.acfun.cn/",
                },
            )
            response.raise_for_status()
            html = response.text

        # 找视频数据
        match = re.search(r"window\.videoInfo\s*=\s*(.*?)</script>", html, re.DOTALL)
        if not match:
            raise ValueError("parse video json info from html fail")

        raw = match.group(1).replace("undefined", "null")
        data = json.loads(raw)

        video_url = data.get("playUrl", "")
        cover_url = data.get("coverUrl", "")
        title = data.get("title", "")
        author_name = data.get("user", {}).get("name", "")

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            author=VideoAuthor(
                name=author_name,
            ),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("AcFun暂不支持直接解析视频ID")

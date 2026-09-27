import asyncio
import yt_dlp
from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class YtDlpParser(BaseParser):
    """
    yt-dlp 通用解析器，支持所有 yt-dlp 能解析的平台
    """

    def __init__(self, proxy: str = ""):
        self.proxy = proxy

    async def parse_share_url(self, share_url: str) -> VideoInfo:
        # yt-dlp 是同步的，放到线程池里跑
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, self._parse_sync, share_url)
        return info

    def _parse_sync(self, share_url: str) -> VideoInfo:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        if self.proxy:
            ydl_opts["proxy"] = self.proxy

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(share_url, download=False)

        # 提取视频地址（选最好的格式）
        video_url = ""
        formats = info.get("formats", [])
        if formats:
            # 找最好的 mp4 格式
            best = None
            for f in reversed(formats):
                if f.get("ext") == "mp4" and f.get("url"):
                    best = f
                    break
            if not best:
                best = formats[-1]
            video_url = best.get("url", "")

        if not video_url:
            video_url = info.get("url", "")

        # 提取封面
        cover_url = info.get("thumbnail", "")

        # 提取标题
        title = info.get("title", "")

        # 提取作者
        author_name = info.get("uploader", "") or info.get("channel", "")
        author_avatar = info.get("uploader_avatar", "") or info.get("channel_avatar", "")

        # 提取图片（图集）
        images = []
        if info.get("images"):
            for img in info["images"]:
                if isinstance(img, dict) and img.get("url"):
                    images.append(ImgInfo(url=img["url"]))
        elif info.get("thumbnails"):
            for img in info["thumbnails"]:
                if isinstance(img, dict) and img.get("url"):
                    images.append(ImgInfo(url=img["url"]))

        return VideoInfo(
            video_url=video_url,
            cover_url=cover_url,
            title=title,
            images=images,
            author=VideoAuthor(
                name=author_name,
                avatar=author_avatar,
            ),
        )

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("yt-dlp通用解析器暂不支持直接解析视频ID")

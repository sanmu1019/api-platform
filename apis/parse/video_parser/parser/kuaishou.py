import json
import re
import fake_useragent
from ..utils import create_async_client, safe_get
from .base import BaseParser, ImgInfo, VideoAuthor, VideoInfo


class KuaiShou(BaseParser):
    """
    快手
    """
    async def parse_share_url(self, share_url: str) -> VideoInfo:
        user_agent = fake_useragent.UserAgent(os="iOS").random
        async with create_async_client(follow_redirects=False) as client:
            response = await safe_get(
                client,
                share_url,
                ("kuaishou.com",),
                headers={
                    "User-Agent": user_agent,
                    "Referer": "https://v.kuaishou.com/",
                },
            )
            response.raise_for_status()
        re_pattern = r"window.INIT_STATE\s*=\s*(.*?)</script>"
        re_result = re.search(re_pattern, response.text)
        if not re_result or len(re_result.groups()) < 1:
            raise Exception("failed to parse video JSON info from HTML")
        json_text = re_result.group(1).strip()
        json_data = json.loads(json_text)
        photo_data = {}
        for json_item in json_data.values():
            if "result" in json_item and "photo" in json_item:
                photo_data = json_item
                break
        if not photo_data:
            raise Exception("failed to parse photo info from INIT_STATE")
        if (result_code := photo_data["result"]) != 1:
            raise Exception(f"获取作品信息失败:result={result_code}")
        data = photo_data["photo"]
        video_url = ""
        if "mainMvUrls" in data and len(data["mainMvUrls"]) > 0:
            video_url = data["mainMvUrls"][0]["url"]
        ext_params_atlas = data.get("ext_params", {}).get("atlas", {})
        atlas_cdn_list = ext_params_atlas.get("cdn", [])
        atlas_list = ext_params_atlas.get("list", [])
        images = []
        if len(atlas_cdn_list) > 0 and len(atlas_list) > 0:
            for atlas in atlas_list:
                images.append(ImgInfo(url=f"https://{atlas_cdn_list[0]}/{atlas}"))
        video_info = VideoInfo(
            video_url=video_url,
            cover_url=data["coverUrls"][0]["url"],
            title=data["caption"],
            author=VideoAuthor(
                uid="",
                name=data["userName"],
                avatar=data["headUrl"],
            ),
            images=images,
        )
        return video_info

    async def parse_video_id(self, video_id: str) -> VideoInfo:
        raise NotImplementedError("快手暂不支持直接解析视频ID")

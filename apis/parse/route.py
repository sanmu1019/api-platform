from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key
from .video_parser.parser import parse_video_share_url, VideoInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/parse", tags=["parse"], dependencies=[Depends(verify_api_key)])


@router.get("/video", name="video_parse")
async def video_parse(url: str = Query(..., description="短视频分享链接，支持皮皮虾、小红书等")):
    """通用短视频无水印解析，支持皮皮虾、小红书等平台。"""
    try:
        video_info = await parse_video_share_url(url)
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "title": video_info.title,
                "video_url": video_info.video_url,
                "cover_url": video_info.cover_url,
                "music_url": video_info.music_url,
                "author": {
                    "uid": video_info.author.uid,
                    "name": video_info.author.name,
                    "avatar": video_info.author.avatar,
                },
                "images": [{"url": img.url, "live_photo_url": img.live_photo_url} for img in video_info.images],
            },
        }
    except ValueError as e:
        # 参数非法 / SSRF 拦截 / 无法解析，归为客户端错误
        logger.warning("视频解析被拒绝: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("视频解析失败")
        raise HTTPException(status_code=500, detail="视频解析失败，请稍后重试")

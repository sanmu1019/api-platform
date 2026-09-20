from __future__ import annotations

import json
import logging
import os

import httpx
from fastapi import APIRouter, Depends, Query

from core.config import settings
from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/music", tags=["music"], dependencies=[Depends(verify_api_key)])

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 代理配置：从环境变量或config读取，格式 http://127.0.0.1:7890
PROXY = os.getenv("HTTP_PROXY", os.getenv("HTTPS_PROXY", ""))


def _client(headers: dict) -> httpx.AsyncClient:
    kwargs = {"timeout": 15, "verify": False, "headers": headers}
    if PROXY:
        kwargs["proxy"] = PROXY
    return httpx.AsyncClient(**kwargs)


@router.get("/qq/search", name="qq_music_search")
async def qq_music_search(keyword: str = Query(..., description="歌曲名或歌手"), limit: int = Query(10, description="返回数量")):
    """搜索QQ音乐，返回歌曲信息和播放地址。"""
    try:
        async with _client({"User-Agent": UA, "Referer": "https://y.qq.com"}) as client:
            search_url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
            params = {
                "w": keyword,
                "format": "json",
                "p": 1,
                "n": limit,
                "cr": 1,
                "g_tk": 5381,
            }
            resp = await client.get(search_url, params=params)
            data = resp.json()

            songs = data.get("data", {}).get("song", {}).get("list", [])
            if not songs:
                return {"code": 404, "msg": "未找到歌曲", "data": []}

            result = []
            for song in songs[:limit]:
                songmid = song.get("songmid", "")
                songname = song.get("songname", "")
                singer = song.get("singer", [{}])[0].get("name", "") if song.get("singer") else ""
                album = song.get("albumname", "")

                vkey_url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
                vkey_params = {
                    "data": json.dumps({
                        "req": {"module": "CDN.SrfCdnDispatchServer", "method": "GetCdnDispatch",
                                "param": {"guid": "3982823384", "calltype": 0, "userip": ""}},
                        "req_0": {"module": "vkey.GetVkeyServer", "method": "CgiGetVkey",
                                  "param": {"guid": "3982823384", "songmid": [songmid], "songtype": [0],
                                            "uin": "0", "loginflag": 1, "platform": "20"}},
                        "comm": {"uin": 0, "format": "json", "ct": 24, "cv": 0},
                    })
                }
                vkey_resp = await client.get(vkey_url, params=vkey_params)
                vkey_data = vkey_resp.json()

                purl = vkey_data.get("req_0", {}).get("data", {}).get("midurlinfo", [{}])[0].get("purl", "")
                play_url = f"https://isure.stream.qqmusic.qq.com/{purl}" if purl else ""

                result.append({
                    "title": songname,
                    "author": singer,
                    "album": album,
                    "songmid": songmid,
                    "play_url": play_url,
                })

            return {"code": 200, "msg": "success", "data": result, "total": len(result)}
    except Exception as e:
        logger.exception("QQ音乐搜索失败")
        return {"code": 500, "msg": str(e), "data": None}


@router.get("/kugou/search", name="kugou_music_search")
async def kugou_music_search(keyword: str = Query(..., description="歌曲名或歌手"), limit: int = Query(10, description="返回数量")):
    """搜索酷狗音乐，返回歌曲信息和播放地址。"""
    try:
        async with _client({"User-Agent": UA, "Referer": "https://www.kugou.com"}) as client:
            search_url = "https://mobilecdn.kugou.com/api/v3/search/song"
            params = {
                "format": "json",
                "keyword": keyword,
                "page": 1,
                "pagesize": limit,
            }
            resp = await client.get(search_url, params=params)
            data = resp.json()

            songs = data.get("data", {}).get("info", [])
            if not songs:
                return {"code": 404, "msg": "未找到歌曲", "data": []}

            result = []
            for song in songs[:limit]:
                song_hash = song.get("hash", "")
                play_url = ""
                cover = song.get("imgurl", "")
                if song_hash:
                    play_params = {
                        "r": "play/getdata",
                        "hash": song_hash,
                        "album_id": 0,
                        "dfid": "2kuKRO3GStCZ0VBY9V12pXeT",
                        "mid": "f679eeece44cf6bec74d2867be4901f7",
                        "platid": 4,
                    }
                    try:
                        play_resp = await client.get("https://wwwapi.kugou.com/yy/index.php", params=play_params)
                        text = play_resp.text
                        if "(" in text:
                            text = text[text.index("(") + 1:].rstrip(")").rstrip(";")
                        play_data = json.loads(text)
                        if play_data.get("err_code") == 0:
                            play_url = play_data.get("data", {}).get("play_url", "")
                            cover = play_data.get("data", {}).get("img", cover)
                    except Exception:
                        pass

                result.append({
                    "title": song.get("songname", ""),
                    "author": song.get("singername", ""),
                    "album": song.get("albumname", ""),
                    "hash": song_hash,
                    "play_url": play_url,
                    "cover": cover,
                })

            return {"code": 200, "msg": "success", "data": result, "total": len(result)}
    except Exception as e:
        logger.exception("酷狗音乐搜索失败")
        return {"code": 500, "msg": str(e), "data": None}

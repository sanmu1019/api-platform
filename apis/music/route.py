from __future__ import annotations

import json
import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from core.config import settings
from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/music", tags=["music"], dependencies=[Depends(verify_api_key)])

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 代理配置：从环境变量或config读取，格式 http://127.0.0.1:7890
PROXY = os.getenv("HTTP_PROXY", os.getenv("HTTPS_PROXY", ""))

QQ_GUID = "3982823384"
QQ_STREAM_HOST = "https://isure.stream.qqmusic.qq.com/"


def _client(headers: dict) -> httpx.AsyncClient:
    kwargs = {
        "timeout": 15,
        "verify": not (settings.debug and not settings.is_production),
        "headers": headers,
    }
    if PROXY:
        kwargs["proxy"] = PROXY
    return httpx.AsyncClient(**kwargs)


def _qq_login(cookie: str) -> tuple[str, str]:
    """从 y.qq.com 的 Cookie 串解析 (uin, authst)；缺任一项返回空串。"""
    pairs = {}
    for part in cookie.split(";"):
        name, _, value = part.strip().partition("=")
        if name:
            pairs[name] = value
    uin = (pairs.get("uin") or pairs.get("wxuin") or "").lstrip("o").lstrip("0")
    authst = pairs.get("qqmusic_key") or pairs.get("qm_keyst") or ""
    return (uin, authst) if uin and authst else ("", "")


async def _qq_purls(client: httpx.AsyncClient, songmids: list[str]) -> tuple[dict[str, str], str]:
    """一次请求取回全部歌曲的播放地址。匿名请求上游一律返回空 purl，需配置 qqmusic_cookie。"""
    uin, authst = _qq_login(settings.qqmusic_cookie)
    if not uin:
        return {}, "未配置 qqmusic_cookie，QQ 音乐不对匿名请求下发播放地址"
    payload = {
        "req_0": {"module": "vkey.GetVkeyServer", "method": "CgiGetVkey",
                  "param": {"guid": QQ_GUID, "songmid": songmids, "songtype": [0] * len(songmids),
                            "uin": uin, "loginflag": 1, "platform": "20"}},
        "comm": {"uin": uin, "authst": authst, "format": "json", "ct": 24, "cv": 0},
    }
    resp = await client.get("https://u.y.qq.com/cgi-bin/musicu.fcg", params={"data": json.dumps(payload)},
                            headers={"Cookie": settings.qqmusic_cookie})
    req_0 = resp.json().get("req_0", {})
    data = req_0.get("data") or {}
    host = (data.get("sip") or [QQ_STREAM_HOST])[0]
    purls = {info["songmid"]: host + info["purl"]
             for info in data.get("midurlinfo") or [] if info.get("songmid") and info.get("purl")}
    if not purls:
        logger.info("QQ 音乐 vkey 未返回播放地址 code=%s（登录态可能已过期，或歌曲需要绿钻）", req_0.get("code"))
        return {}, "未取到播放地址：qqmusic_cookie 可能已过期，或歌曲需要绿钻"
    return purls, ""


@router.get("/qq/search", name="qq_music_search")
async def qq_music_search(keyword: str = Query(..., description="歌曲名或歌手"), limit: int = Query(10, ge=1, le=30, description="返回数量")):
    """搜索QQ音乐，返回歌曲信息；配置 qqmusic_cookie 后附带播放地址。"""
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
                raise HTTPException(status_code=404, detail="未找到歌曲")

            songs = songs[:limit]
            songmids = [song.get("songmid", "") for song in songs]
            purls, note = await _qq_purls(client, [m for m in songmids if m])

            result = []
            for song, songmid in zip(songs, songmids):
                singer = song.get("singer", [{}])[0].get("name", "") if song.get("singer") else ""
                result.append({
                    "title": song.get("songname", ""),
                    "author": singer,
                    "album": song.get("albumname", ""),
                    "songmid": songmid,
                    "play_url": purls.get(songmid, ""),
                    "web_url": f"https://y.qq.com/n/ryqq/songDetail/{songmid}" if songmid else "",
                })

            body = {"code": 200, "msg": "success", "data": result, "total": len(result)}
            if note:
                body["note"] = note
            return body
    except HTTPException:
        raise
    except Exception:
        logger.exception("QQ音乐搜索失败")
        raise HTTPException(status_code=502, detail="上游音乐服务请求失败")


@router.get("/kugou/search", name="kugou_music_search")
async def kugou_music_search(keyword: str = Query(..., description="歌曲名或歌手"), limit: int = Query(10, ge=1, le=30, description="返回数量")):
    """搜索酷狗音乐，返回歌曲信息和网页链接。

    酷狗取播放地址的接口（play/getdata）现在要求签名和登录态，匿名请求一律 err_code=30020，
    因此不再逐首请求，play_url 固定为空。
    """
    try:
        async with _client({"User-Agent": UA, "Referer": "https://www.kugou.com"}) as client:
            # mobilecdn.kugou.com 的 HTTPS 证书与域名不匹配，只能走 http；这里只取公开的搜索元数据。
            search_url = "http://mobilecdn.kugou.com/api/v3/search/song"
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
                raise HTTPException(status_code=404, detail="未找到歌曲")

            result = []
            for song in songs[:limit]:
                song_hash = song.get("hash", "")
                result.append({
                    "title": song.get("songname", ""),
                    "author": song.get("singername", ""),
                    "album": song.get("album_name", "") or song.get("albumname", ""),
                    "hash": song_hash,
                    "play_url": "",
                    "web_url": f"https://www.kugou.com/song/#hash={song_hash}" if song_hash else "",
                    "cover": song.get("imgurl", ""),
                })

            return {"code": 200, "msg": "success", "data": result, "total": len(result)}
    except HTTPException:
        raise
    except Exception:
        logger.exception("酷狗音乐搜索失败")
        raise HTTPException(status_code=502, detail="上游音乐服务请求失败")

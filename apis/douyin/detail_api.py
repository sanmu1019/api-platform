"""抖音官方详情接口解析。

从 `E:\\wxbot-ipad` 的 DouyinParser 插件移植而来。

**为什么要移植**：本项目原本抓分享页 HTML、解析 `window._ROUTER_DATA`
（见 service.py 的 `_extract_router_aweme_item`）。隔壁项目 2026 年 8 月已经
放弃这条路，理由写在它的 README 里：「分享页 `window._ROUTER_DATA` 在 8 月改版后
不再稳定存在」。线上日志里 `douyin_parse` 275 次调用中 19 次 400，报的正是
"页面已获取，但没有识别到视频/图文数据"——就是这个症状。

**移植范围**：只搬"怎么拿到 aweme 原始字典"这一段（官方接口 + a_bogus 签名 +
ttwid）。输出规范化沿用 service.py 里现成的 `_normalize_aweme`，不重复实现。

a_bogus 是逆向出来的签名算法。抖音一旦更换算法，所有解析会**同时且持续**失败，
而单次失败看起来和链接失效一模一样 —— 所以只有连续失败才值得告警。
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional
from urllib.parse import quote

import requests

from core.config import settings
from .a_bogus import generate_a_bogus

logger = logging.getLogger(__name__)

DETAIL_API_URL = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
TTWID_API_URL = "https://ttwid.bytedance.com/ttwid/union/register/"
ITEM_ID_RE = re.compile(r"/(?:video|note|slides|share)/?(\d{10,})")
DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
RETRY_STATUS_CODES = frozenset({403, 429, 500, 502, 503, 504})
RETRY_DELAYS = (0.35, 0.8)
SIGNATURE_FAILURE_ALERT_THRESHOLD = 3

_TTWID_TTL = 3600.0
_ttwid_cache: Optional[str] = None
_ttwid_cache_time = 0.0
_consecutive_failures = 0


def extract_item_id(source_url: str) -> str:
    match = ITEM_ID_RE.search(str(source_url or ""))
    return match.group(1) if match else ""


def _build_detail_query(item_id: str) -> str:
    params = {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "aweme_id": item_id,
        "update_version_code": "170400",
        "pc_client_type": "1",
        "version_code": "170400",
        "version_name": "17.4.0",
        "cookie_enabled": "true",
        "screen_width": "1536",
        "screen_height": "864",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Chrome",
        "browser_version": "123.0.0.0",
        "browser_online": "true",
        "engine_name": "Blink",
        "engine_version": "123.0.0.0",
        "os_name": "Windows",
        "os_version": "10",
        "cpu_core_num": "16",
        "device_memory": "8",
        "platform": "PC",
        "downlink": "10",
        "effective_type": "4g",
        "round_trip_time": "50",
    }
    return "&".join(f"{key}={value}" for key, value in params.items())


def _get_ttwid(session: requests.Session, timeout: float) -> str:
    global _ttwid_cache, _ttwid_cache_time
    now = time.time()
    if _ttwid_cache and now - _ttwid_cache_time < _TTWID_TTL:
        return _ttwid_cache

    response = session.post(
        TTWID_API_URL,
        json={
            "region": "cn",
            "aid": 1768,
            "needFid": False,
            "service": "www.ixigua.com",
            "migrate_info": {"ticket": "", "source": "node"},
            "cbUrlProtocol": "https",
            "union": True,
        },
        timeout=timeout,
    )
    if response.status_code != 200:
        raise RuntimeError(f"获取抖音 ttwid 失败，状态码: {response.status_code}")

    match = re.search(r"ttwid=([^;]+)", response.headers.get("Set-Cookie", ""))
    if not match:
        raise RuntimeError("获取抖音 ttwid 失败: 响应中未包含 ttwid")

    _ttwid_cache = match.group(1)
    _ttwid_cache_time = now
    return _ttwid_cache


def _extract_aweme_detail(response: requests.Response) -> tuple[Optional[dict[str, Any]], str]:
    """取出 aweme_detail，或说明为什么不可用。

    刻意不抛异常：被拒绝的 a_bogus 签名通常表现为 HTTP 200 + 空body，
    调用方需要能把它当成"可重试"而不是"致命错误"。
    """
    if response.status_code != 200:
        return None, f"抖音详情接口失败，状态码: {response.status_code}"
    try:
        payload = response.json()
    except ValueError as exc:
        return None, f"抖音详情接口返回不是 JSON: {exc}"
    if not isinstance(payload, dict) or payload.get("status_code") not in (0, "0"):
        return None, "抖音详情接口未返回有效数据"
    aweme = payload.get("aweme_detail")
    if not isinstance(aweme, dict) or not aweme.get("aweme_id"):
        return None, "抖音详情接口未返回作品数据"
    return aweme, ""


def fetch_aweme_detail(
    item_id: str,
    *,
    timeout: float = 6.0,
    session: requests.Session | None = None,
) -> tuple[Optional[dict[str, Any]], str]:
    """按 item_id 取原始 aweme 字典。返回 (aweme, 失败原因)。"""
    global _consecutive_failures

    owns_session = session is None
    session = session or requests.Session()
    if settings.douyin_proxy:
        session.proxies = {"http": settings.douyin_proxy, "https": settings.douyin_proxy}
    query = _build_detail_query(item_id)
    aweme: Optional[dict[str, Any]] = None
    failure = "抖音详情接口未发起请求"

    try:
        for attempt in range(len(RETRY_DELAYS) + 1):
            global _ttwid_cache, _ttwid_cache_time
            try:
                ttwid = _get_ttwid(session, timeout)
            except (RuntimeError, requests.RequestException) as exc:
                return None, str(exc)

            signature = generate_a_bogus(query, DESKTOP_USER_AGENT)
            detail_url = f"{DETAIL_API_URL}?{query}&a_bogus={quote(signature, safe='')}"
            try:
                response = session.get(
                    detail_url,
                    headers={
                        "Cookie": f"ttwid={ttwid}",
                        "Referer": "https://www.douyin.com/",
                        "User-Agent": DESKTOP_USER_AGENT,
                    },
                    timeout=timeout,
                )
            except requests.RequestException as exc:
                return None, f"网络请求失败: {exc}"

            aweme, failure = _extract_aweme_detail(response)
            if aweme:
                break
            if attempt >= len(RETRY_DELAYS):
                break
            # 走到这里的 HTTP 200 说明签名在传输层被接受但 body 不可用，
            # 这正是 a_bogus 被拒的典型形态，值得重试；此外只重试瞬时错误码。
            if response.status_code != 200 and response.status_code not in RETRY_STATUS_CODES:
                break
            logger.info("[douyin] 详情接口重试 %s: %s", attempt + 1, failure)
            _ttwid_cache = None
            _ttwid_cache_time = 0.0
            time.sleep(RETRY_DELAYS[attempt])
    finally:
        if owns_session:
            session.close()

    if aweme:
        _consecutive_failures = 0
        return aweme, ""

    _consecutive_failures += 1
    if _consecutive_failures >= SIGNATURE_FAILURE_ALERT_THRESHOLD:
        logger.error(
            "[douyin][签名可能失效] 详情接口连续 %s 次取不到数据，最后一次: %s。"
            "若持续，多半是抖音更换了 a_bogus 算法或 web 端参数，需更新 apis/douyin/a_bogus.py",
            _consecutive_failures, failure,
        )
    return None, failure


def signature_health() -> dict[str, Any]:
    """签名健康状态，供后台/监控查询。

    a_bogus 是逆向出来的算法，抖音一改就**全线持续**失效；而单次失败和
    "链接失效"表现完全一样，没有诊断价值。所以这里暴露的是"连续失败次数"，
    由调用方据此判断是否需要告警（阈值见 `alert_threshold`）。
    """
    return {
        "consecutive_failures": _consecutive_failures,
        "alert_threshold": SIGNATURE_FAILURE_ALERT_THRESHOLD,
        "alerting": _consecutive_failures >= SIGNATURE_FAILURE_ALERT_THRESHOLD,
        "ttwid_cached": bool(_ttwid_cache),
    }

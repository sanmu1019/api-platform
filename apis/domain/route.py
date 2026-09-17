"""域名信息查询：ICP 备案 + WHOIS。

从 `E:\\wxbot-ipad` 的 mmm 插件移植。那边三条命令（ICP / whois / 域名查询）
共用同一份域名解析，这里保持同样的结构。

移植它是因为本平台原本没有域名类接口，而它只是两个 HTTP 调用加格式化，
不依赖微信、不依赖 AI，搬过来成本很低。

WHOIS 上游有两个坑（在 wxbot 那边踩过）：

1. 同一份数据给了两遍：外层是 `Domain Name` 这样的 Title Case，
   内层 `data` 又是 `domain_name` 这样的 snake_case。取内层、外层兜底。
2. **未注册的域名照样返回 code 200**，只是字段全空。所以不能照字段逐条
   打"未知"，查不到就明确说查不到。
3. `sponsoring_registrar` 恒为空串（实测 baidu.com / qq.com / github.com 内外层
   都是空），「注册商」只能从 `registrar_url` 反推，并在响应里标明是推断值。
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key

router = APIRouter(prefix="/api/domain", tags=["domain"], dependencies=[Depends(verify_api_key)])

ICP_API = "https://openapi.dwo.cc/api/icp"
WHOIS_API = "https://v2.xxapi.cn/api/whois"
DOMAIN_RE = re.compile(
    r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}"
)
# 外层 Title Case 与内层 snake_case 的对应，以及展示用的中文名
WHOIS_FIELDS = (
    ("registrant", "Registrant", "注册人"),
    ("registrant_contact_email", "Registrant Contact Email", "邮箱"),
    ("registrar_url", "Registrar URL", "注册商网址"),
)

# 上游 `sponsoring_registrar` **恒为空串**（实测 baidu.com / qq.com / github.com
# 三个域名的内外层都是空），但 `registrar_url` 一直有值。与其让「注册商」这个
# 字段永远缺席，不如从网址反推 —— 但必须标明是推断值，不能让调用方当成
# 注册局权威数据。
KNOWN_REGISTRARS = {
    "markmonitor.com": "MarkMonitor",
    "godaddy.com": "GoDaddy",
    "namecheap.com": "Namecheap",
    "networksolutions.com": "Network Solutions",
    "tucows.com": "Tucows",
    "hichina.com": "阿里云（万网）",
    "aliyun.com": "阿里云",
    "xinnet.com": "新网",
    "ename.net": "易名",
    "dnspod.com": "DNSPod",
    "cloudflare.com": "Cloudflare",
    "west.cn": "西部数码",
    "bizcn.com": "商务中国",
}


def _registrar_from_url(value: str) -> str:
    """从注册商网址反推注册商名。

    先拿主机名的可注册域去查已知表；查不到就退化为首字母大写的主标签。
    这是启发式推断，所以调用方那边会同时拿到 `注册商来源` 标记。
    """
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urllib.parse.urlparse(text if "://" in text else f"http://{text}")
    host = (parsed.hostname or "").lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return ""
    if host in KNOWN_REGISTRARS:
        return KNOWN_REGISTRARS[host]
    label = host.split(".")[0]
    return label[:1].upper() + label[1:] if label else ""


def normalize_domain(value: str) -> str:
    """接受裸域名或整条 URL，取出主机名。非法输入返回空串。"""
    candidate = str(value or "").strip().strip("，。！？,.;；")
    if not candidate:
        return ""
    parsed = urllib.parse.urlparse(
        candidate if "://" in candidate else f"https://{candidate}"
    )
    domain = (parsed.hostname or "").strip(".").lower()
    return domain if DOMAIN_RE.fullmatch(domain) else ""


def _get_json(url: str, params: dict[str, str], timeout: float) -> Any:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url}?{query}", headers={"User-Agent": "api-platform/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _whois_value(record: dict, snake: str, title: str):
    inner = record.get("data")
    if isinstance(inner, dict) and inner.get(snake) not in (None, ""):
        return inner.get(snake)
    value = record.get(title)
    return value if value not in (None, "") else None


def _format_time(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return datetime.strptime(text[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%d")
    except ValueError:
        return text


def _days_until(value) -> int | None:
    text = str(value or "").strip()
    try:
        stamp = datetime.strptime(text[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (stamp - datetime.now(timezone.utc)).days


def query_icp(domain: str, timeout: float) -> dict[str, Any]:
    try:
        payload = _get_json(ICP_API, {"domain": domain}, timeout)
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}", "records": []}
    if not isinstance(payload, dict) or payload.get("code") != 200:
        return {"available": False, "error": str((payload or {}).get("msg") or "接口返回异常"), "records": []}
    rows = payload.get("data")
    if not isinstance(rows, list) or not rows:
        return {"available": False, "error": "", "records": []}
    return {
        "available": True,
        "error": "",
        "records": [
            {
                "license": item.get("serviceLicence") or "",
                "unit": item.get("unitName") or "",
                "nature": item.get("natureName") or "",
                "updated": item.get("updateTime") or "",
            }
            for item in rows[:5] if isinstance(item, dict)
        ],
    }


def query_whois(domain: str, timeout: float) -> dict[str, Any]:
    try:
        payload = _get_json(WHOIS_API, {"domain": domain}, timeout)
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}", "info": {}}
    if not isinstance(payload, dict) or payload.get("code") != 200:
        return {"available": False, "error": str((payload or {}).get("msg") or "接口返回异常"), "info": {}}
    record = payload.get("data")
    if not isinstance(record, dict) or not record:
        return {"available": False, "error": "", "info": {}}

    info: dict[str, Any] = {}
    for snake, title, label in WHOIS_FIELDS:
        value = str(_whois_value(record, snake, title) or "").strip()
        if value:
            info[label] = value

    created = _format_time(_whois_value(record, "registration_time", "Registration Time"))
    if created:
        info["注册时间"] = created
    raw_expire = _whois_value(record, "expiration_time", "Expiration Time")
    expires = _format_time(raw_expire)
    if expires:
        remaining = _days_until(raw_expire)
        info["到期时间"] = expires
        if remaining is not None:
            info["剩余天数"] = remaining

    status = str(_whois_value(record, "domain_status", "domain_status") or "").strip()
    if status:
        # 上游把 "serverUpdateProhibited https://icann.org/epp#..." 拼在一起，
        # 后面那截 URL 对调用方没用
        info["状态"] = status.split()[0]

    servers = _whois_value(record, "dns_serve", "DNS Serve")
    if isinstance(servers, list) and servers:
        info["DNS"] = [str(x).strip() for x in servers if str(x).strip()]

    # 上游的 sponsoring_registrar 恒空，所以「注册商」实际只能靠网址反推
    if "注册商" not in info:
        derived = _registrar_from_url(info.get("注册商网址", ""))
        if derived:
            info["注册商"] = derived
            info["注册商来源"] = "推断自 registrar_url"

    # 未注册的域名接口照样返回 200，只是字段全空
    return {"available": bool(info), "error": "", "info": info}


@router.get("/whois", name="domain_whois")
def whois(
    domain: str = Query(..., min_length=3, max_length=253, description="域名或整条网址"),
    timeout: float = Query(10.0, ge=2.0, le=25.0),
) -> dict:
    target = normalize_domain(domain)
    if not target:
        raise HTTPException(status_code=400, detail="域名格式不正确")
    result = query_whois(target, timeout)
    if result["error"]:
        raise HTTPException(status_code=502, detail=f"WHOIS 查询失败：{result['error']}")
    return {
        "code": 200,
        "msg": "success" if result["available"] else "no data",
        "data": {"domain": target, "available": result["available"], "whois": result["info"]},
    }


@router.get("/icp", name="domain_icp")
def icp(
    domain: str = Query(..., min_length=3, max_length=253),
    timeout: float = Query(10.0, ge=2.0, le=25.0),
) -> dict:
    target = normalize_domain(domain)
    if not target:
        raise HTTPException(status_code=400, detail="域名格式不正确")
    result = query_icp(target, timeout)
    if result["error"]:
        raise HTTPException(status_code=502, detail=f"ICP 查询失败：{result['error']}")
    return {
        "code": 200,
        "msg": "success" if result["available"] else "no data",
        "data": {"domain": target, "available": result["available"], "records": result["records"]},
    }


@router.get("/info", name="domain_info")
def domain_info(
    domain: str = Query(..., min_length=3, max_length=253),
    timeout: float = Query(10.0, ge=2.0, le=25.0),
) -> dict:
    """ICP + WHOIS 一次给全。

    两个数据源互不覆盖：ICP 只有中国大陆主体有，WHOIS 是注册局数据。
    所以任一侧查不到或失败都不影响另一侧，各自带 available/error。
    """
    target = normalize_domain(domain)
    if not target:
        raise HTTPException(status_code=400, detail="域名格式不正确")
    icp_result = query_icp(target, timeout)
    whois_result = query_whois(target, timeout)
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "domain": target,
            "icp": {
                "available": icp_result["available"],
                "error": icp_result["error"],
                "records": icp_result["records"],
            },
            "whois": {
                "available": whois_result["available"],
                "error": whois_result["error"],
                "info": whois_result["info"],
            },
        },
    }

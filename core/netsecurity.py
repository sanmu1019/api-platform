"""统一的出站请求网络安全校验（SSRF 防护）。

所有由用户传入 URL / 主机、再由服务端发起请求的地方都应复用这里的校验，
防止访问回环、私网、链路本地、云元数据等内部地址。
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# 明确禁止的主机名（含尾点、本地域名变体）
_FORBIDDEN_HOSTNAMES = {"localhost", ""}
_FORBIDDEN_SUFFIXES = (".localhost", ".localdomain", ".local", ".internal")


def _ip_is_blocked(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local      # 含 169.254.0.0/16 云元数据
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def check_public_host(host: str | None, resolve_dns: bool = True) -> tuple[bool, str]:
    """校验主机（IP 或域名）只会访问公网地址。

    返回 (是否允许, 原因)。域名会在 DNS 解析后对所有结果 IP 再校验一次，
    防止解析到内网地址（DNS rebinding）。
    """
    if not host:
        return False, "主机名为空"

    raw = host.strip()
    h = raw.lower().rstrip(".")

    if h in _FORBIDDEN_HOSTNAMES:
        return False, "禁止访问本地主机"
    if any(h == s.lstrip(".") or h.endswith(s) for s in _FORBIDDEN_SUFFIXES):
        return False, "禁止访问本地主机名"

    # 字面量 IP
    try:
        ip = ipaddress.ip_address(raw.split("%")[0])
    except ValueError:
        ip = None
    if ip is not None:
        if _ip_is_blocked(ip):
            return False, f"禁止访问内网/保留地址 {raw}"
        return True, ""

    # 域名：DNS 解析后逐 IP 校验
    if resolve_dns:
        try:
            infos = socket.getaddrinfo(raw, None)
        except socket.gaierror:
            return False, "无法解析该域名"
        except Exception:
            return False, "域名解析异常"
        if not infos:
            return False, "域名无解析结果"
        for info in infos:
            ip_str = (info[4][0] or "").split("%")[0]
            try:
                resolved = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            if _ip_is_blocked(resolved):
                return False, f"域名解析到内网/保留地址 {ip_str}"
    return True, ""


def resolve_public_host(host: str | None) -> tuple[bool, str, list[str]]:
    """Validate a host and return the validated addresses used for the connection."""
    if not host:
        return False, "主机名为空", []

    raw = host.strip()
    h = raw.lower().rstrip(".")
    if h in _FORBIDDEN_HOSTNAMES:
        return False, "禁止访问本地主机", []
    if any(h == s.lstrip(".") or h.endswith(s) for s in _FORBIDDEN_SUFFIXES):
        return False, "禁止访问本地主机名", []

    try:
        ip = ipaddress.ip_address(raw.split("%")[0])
    except ValueError:
        ip = None
    if ip is not None:
        if _ip_is_blocked(ip):
            return False, f"禁止访问内网/保留地址 {raw}", []
        return True, "", [str(ip)]

    try:
        infos = socket.getaddrinfo(raw, None)
    except socket.gaierror:
        return False, "无法解析该域名", []
    except Exception:
        return False, "域名解析异常", []
    if not infos:
        return False, "域名无解析结果", []

    addresses: list[str] = []
    for info in infos:
        ip_str = (info[4][0] or "").split("%")[0]
        try:
            resolved = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _ip_is_blocked(resolved):
            return False, f"域名解析到内网/保留地址 {ip_str}", []
        if ip_str not in addresses:
            addresses.append(ip_str)
    if not addresses:
        return False, "域名无有效解析结果", []
    return True, "", addresses


def check_public_url(url: str | None, resolve_dns: bool = True) -> tuple[bool, str]:
    """校验 URL 的目标主机只会访问公网地址。"""
    if not url:
        return False, "URL 为空"
    try:
        parsed = urlparse(url)
        if parsed.scheme.lower() not in {"http", "https"}:
            return False, "仅允许 HTTP/HTTPS URL"
        if parsed.username is not None or parsed.password is not None:
            return False, "URL 不允许包含用户信息"
        # Force validation of malformed ports instead of letting the HTTP client
        # interpret them differently.
        _ = parsed.port
        host = parsed.hostname
    except Exception:
        return False, "URL 格式错误"
    if not host:
        return False, "URL 缺少主机名"
    return check_public_host(host, resolve_dns=resolve_dns)

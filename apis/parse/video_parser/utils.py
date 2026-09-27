import asyncio
import os
import re
from urllib.parse import parse_qs, urljoin, urlparse
import httpx
from core.config import settings
from core.netsecurity import check_public_url


_REDIRECT_STATUS = {301, 302, 303, 307, 308}


def get_val_from_url_by_query_key(url: str, query_key: str) -> str:
    url_res = urlparse(url)
    url_query = parse_qs(url_res.query, keep_blank_values=True)
    try:
        query_val = url_query[query_key][0]
    except KeyError:
        raise KeyError(f"url中不存在query参数: {query_key}")
    if len(query_val) == 0:
        raise ValueError(f"url中query参数值长度为0: {query_key}")
    return url_query[query_key][0]


def create_async_client(**kwargs) -> httpx.AsyncClient:
    proxy = getattr(settings, "douyin_proxy", None)
    if proxy:
        kwargs["proxy"] = proxy
    # 默认开启TLS校验，开发环境可以通过debug配置关闭
    # Development may opt out; production must always verify certificates.
    kwargs.setdefault(
        "verify",
        not (getattr(settings, "debug", False) and not getattr(settings, "is_production", False)),
    )
    return httpx.AsyncClient(**kwargs)


def validate_allowed_url(url: str, allowed_domains: tuple[str, ...]) -> None:
    """Validate scheme, URL shape, allowlisted host, and public DNS resolution."""
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("仅允许 HTTP/HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL 不允许包含用户信息")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("URL 端口格式错误") from exc
    if port is not None and port not in {80, 443}:
        raise ValueError("URL 只允许使用 80/443 端口")
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        raise ValueError("URL 缺少主机名")
    if not any(host == domain or host.endswith("." + domain) for domain in allowed_domains):
        raise ValueError("URL 主机不在允许的域名范围内")

    ok, reason = check_public_url(url, resolve_dns=True)
    if not ok:
        raise ValueError(reason)


async def safe_get(
    client: httpx.AsyncClient,
    url: str,
    allowed_domains: tuple[str, ...],
    *,
    max_redirects: int = 5,
    **kwargs,
) -> httpx.Response:
    """GET a URL while validating every redirect target before requesting it."""
    current = url
    for _ in range(max_redirects + 1):
        await asyncio.to_thread(validate_allowed_url, current, allowed_domains)
        response = await client.get(current, follow_redirects=False, **kwargs)
        if response.status_code not in _REDIRECT_STATUS:
            await asyncio.to_thread(validate_allowed_url, str(response.url), allowed_domains)
            return response

        location = response.headers.get("location")
        await response.aclose()
        if not location:
            raise ValueError("重定向响应缺少 Location")
        current = urljoin(current, location)
    raise ValueError("重定向次数过多")

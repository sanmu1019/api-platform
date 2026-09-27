from urllib.parse import urlparse
from .base import VideoInfo, VideoSource, ImgInfo, VideoAuthor
from .kuaishou import KuaiShou
from .pipixia import PiPiXia
from .redbook import RedBook
from .weibo import WeiBo
from .xigua import XiGua
from .acfun import AcFun
from .ytdlp import YtDlpParser
from core.config import settings

video_source_info_mapping = {
    VideoSource.KuaiShou: {
        "domain_list": ["v.kuaishou.com", "www.kuaishou.com"],
        "parser": KuaiShou,
    },
    VideoSource.PiPiXia: {
        "domain_list": ["h5.pipix.com", "www.pipix.com"],
        "parser": PiPiXia,
    },
    VideoSource.RedBook: {
        "domain_list": ["www.xiaohongshu.com", "xhslink.com", "xhslink.cn"],
        "parser": RedBook,
    },
    VideoSource.WeiBo: {
        "domain_list": ["weibo.com", "weibo.cn", "m.weibo.cn"],
        "parser": WeiBo,
    },
    VideoSource.XiGua: {
        "domain_list": ["v.ixigua.com", "www.ixigua.com"],
        "parser": XiGua,
    },
    VideoSource.AcFun: {
        "domain_list": ["www.acfun.cn", "m.acfun.cn"],
        "parser": AcFun,
    },
}


def _is_domain_match(url: str, domain_list: list[str]) -> bool:
    """严格校验URL的hostname是否在域名列表里"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname = hostname.lower()
        for domain in domain_list:
            domain = domain.lower()
            if hostname == domain or hostname.endswith("." + domain):
                return True
        return False
    except Exception:
        return False


async def parse_video_share_url(share_url: str) -> VideoInfo:
    source = ""
    for item_source, item_source_info in video_source_info_mapping.items():
        if _is_domain_match(share_url, item_source_info["domain_list"]):
            source = item_source
            break

    # 优先用专用解析器
    if source:
        url_parser = video_source_info_mapping[source]["parser"]
        _obj = url_parser()
        video_info = await _obj.parse_share_url(share_url)
        return video_info

    # 找不到匹配平台，用 yt-dlp 通用解析器试试（不携带任何cookie）。
    # 代理不应成为跳过 SSRF/DNS 校验的理由；代理端的 DNS 结果不可控。
    # SSRF 防护：yt-dlp 接受任意域名，必须先确认目标不是内网/云元数据地址。
    # - 未配置代理：服务端直连，做完整 DNS 解析后校验（防 DNS rebinding）。
    from core.netsecurity import check_public_url
    proxy = getattr(settings, "douyin_proxy", "") or ""
    ok, reason = check_public_url(share_url, resolve_dns=True)
    if not ok:
        raise ValueError(f"不允许解析该地址：{reason}")

    try:
        parser = YtDlpParser(proxy=proxy)
        video_info = await parser.parse_share_url(share_url)
        return video_info
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"无法解析该链接: {str(e)}")

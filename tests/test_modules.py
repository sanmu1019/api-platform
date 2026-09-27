"""domain / divination / wxsph / parse / tools2 模块测试。所有网络调用均被 monkeypatch。"""
import httpx
import pytest
from fastapi.testclient import TestClient

from core.depends import verify_api_key
from main import app

import apis.domain.route as domain_route
import apis.extra2.route as extra2_route
import apis.parse.route as parse_route
import apis.wxsph.route as wxsph_route
from apis.parse.video_parser.parser.base import ImgInfo, VideoAuthor, VideoInfo


_seq = iter(range(1, 10**6))


@pytest.fixture()
def client():
    # 每个用例独立的对端地址，避免全量运行时撞上按 IP 的限流（429）
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app, client=(f"modtest-{next(_seq)}", 50000))
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


# ───────────── domain ───────────────

WHOIS_OK = {
    "code": 200,
    "data": {
        "Registrant": "outer",
        "data": {
            "registrant": "Beijing Baidu",
            "registrar_url": "http://www.markmonitor.com",
            "registration_time": "1999-10-11T11:05:17Z",
            "expiration_time": "2099-10-11T11:05:17Z",
            "domain_status": "clientDeleteProhibited https://icann.org/epp#x",
            "dns_serve": ["ns1.baidu.com", " "],
        },
    },
}
ICP_OK = {"code": 200, "data": [{"serviceLicence": "京ICP证030173号", "unitName": "百度", "natureName": "企业", "updateTime": "2024"}]}


def _fake_get_json(icp=ICP_OK, whois=WHOIS_OK):
    def fake(url, params, timeout):
        payload = icp if url == domain_route.ICP_API else whois
        if isinstance(payload, Exception):
            raise payload
        return payload
    return fake


def test_domain_whois_success(client, monkeypatch):
    monkeypatch.setattr(domain_route, "_get_json", _fake_get_json())
    r = client.get("/api/domain/whois", params={"domain": "https://WWW.Baidu.com/path"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["domain"] == "www.baidu.com" and data["available"] is True
    info = data["whois"]
    assert info["注册人"] == "Beijing Baidu"
    assert info["注册时间"] == "1999-10-11"
    assert info["状态"] == "clientDeleteProhibited"
    assert info["DNS"] == ["ns1.baidu.com"]
    assert info["注册商"] == "MarkMonitor"
    assert isinstance(info["剩余天数"], int)


def test_domain_whois_unregistered(client, monkeypatch):
    monkeypatch.setattr(domain_route, "_get_json", _fake_get_json(whois={"code": 200, "data": {"data": {}, "x": ""}}))
    r = client.get("/api/domain/whois", params={"domain": "nope-xyz.com"})
    assert r.status_code == 200
    assert r.json()["msg"] == "no data" and r.json()["data"]["available"] is False


def test_domain_icp_success(client, monkeypatch):
    monkeypatch.setattr(domain_route, "_get_json", _fake_get_json())
    r = client.get("/api/domain/icp", params={"domain": "baidu.com"})
    assert r.status_code == 200
    rec = r.json()["data"]["records"][0]
    assert rec == {"license": "京ICP证030173号", "unit": "百度", "nature": "企业", "updated": "2024"}


@pytest.mark.parametrize("path", ["/api/domain/whois", "/api/domain/icp", "/api/domain/info"])
@pytest.mark.parametrize("domain,status", [("not a domain", 400), ("ab", 422), ("localhost", 400)])
def test_domain_invalid(client, path, domain, status):
    assert client.get(path, params={"domain": domain}).status_code == status


def test_domain_timeout_validation(client):
    assert client.get("/api/domain/icp", params={"domain": "baidu.com", "timeout": 100}).status_code == 422


def test_domain_upstream_failure(client, monkeypatch):
    monkeypatch.setattr(domain_route, "_get_json", _fake_get_json(icp=OSError("boom"), whois={"code": 500, "msg": "限流"}))
    r1 = client.get("/api/domain/icp", params={"domain": "baidu.com"})
    assert r1.status_code == 502 and "OSError" in r1.json()["detail"]
    r2 = client.get("/api/domain/whois", params={"domain": "baidu.com"})
    assert r2.status_code == 502 and "限流" in r2.json()["detail"]


def test_domain_info_partial_failure(client, monkeypatch):
    monkeypatch.setattr(domain_route, "_get_json", _fake_get_json(icp=OSError("boom")))
    r = client.get("/api/domain/info", params={"domain": "baidu.com"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["icp"]["available"] is False and data["icp"]["error"] == "OSError"
    assert data["whois"]["available"] is True


# ───────────── divination（纯本地计算） ─────────────

def test_plum_time_success_deterministic(client):
    params = {"year": 2024, "month": 5, "day": 20, "hour": 10, "question": "测试"}
    r1 = client.get("/api/divination/plum", params=params)
    r2 = client.get("/api/divination/plum", params=params)
    assert r1.status_code == 200 and r1.json() == r2.json()
    data = r1.json()["data"]
    assert data["question"] == "测试" and data["method"] == "时间"
    assert set(data["hexagrams"]) == {"ben", "hu", "bian"}
    assert 1 <= data["analysis"]["moving_line"] <= 6
    assert data["time"]["year"] == 2024 and data["disclaimer"]
    assert "问：测试" in data["text"]


def test_plum_number_success(client):
    r = client.get("/api/divination/number", params={"number": 258, "hour": 10, "month": 3})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["method"] == "数字" and "258" in data["text"]
    assert data["time"]["hour"] == 10


@pytest.mark.parametrize("params", [
    {"number": 99}, {"number": 1000}, {"number": 258, "hour": 24}, {"number": 258, "month": 0},
])
def test_plum_number_invalid(client, params):
    assert client.get("/api/divination/number", params=params).status_code == 422


def test_plum_time_invalid(client):
    assert client.get("/api/divination/plum", params={"year": 2023, "month": 2, "day": 30, "hour": 1}).status_code == 400
    assert client.get("/api/divination/plum", params={"month": 13}).status_code == 422
    assert client.get("/api/divination/plum", params={"question": "x" * 101}).status_code == 422


# ─────────────── wxsph ─────────────

SPH_URL = "https://weixin.qq.com/sph/Abc123"


@pytest.fixture()
def sph_env(monkeypatch):
    wxsph_route._cache.clear() if hasattr(wxsph_route._cache, "clear") else None
    monkeypatch.setattr(wxsph_route, "_get_cookie", lambda: "cookie")
    calls = []

    def fake_post(url, payload, headers, timeout=15):
        calls.append(url)
        if url == wxsph_route.YUANBAO_PARSE_URL:
            return {"data": {"playable_url": "https://x/y?token=TK&eid=EID", "title": "t0"}}
        return {"errCode": 0, "data": {
            "feedInfo": {"h264VideoInfo": {"videoUrl": "https://v/1.mp4"}, "title": "标题", "coverUrl": "https://c/1.jpg"},
            "authorInfo": {"nickname": "作者"},
        }}

    monkeypatch.setattr(wxsph_route, "_post_json", fake_post)
    yield calls
    if hasattr(wxsph_route._cache, "clear"):
        wxsph_route._cache.clear()


def test_wxsph_success_and_cache(client, sph_env):
    r = client.get("/api/wxsph/parse", params={"url": f"看看这个 {SPH_URL}?from=1 哈"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data == {
        "title": "标题", "cover": "https://c/1.jpg", "video_url": "https://v/1.mp4",
        "author": "作者", "share_url": SPH_URL + "?from=1", "source": "wechat_channels",
    }
    n = len(sph_env)
    assert client.get("/api/wxsph/parse", params={"url": f"{SPH_URL}?from=1"}).status_code == 200
    assert len(sph_env) == n  # 命中缓存


@pytest.mark.parametrize("url", ["https://evil.com/sph/abc", "https://weixin.qq.com/other", "hello"])
def test_wxsph_invalid_url(client, url):
    assert client.get("/api/wxsph/parse", params={"url": url}).status_code == 400


def test_wxsph_missing_url(client):
    assert client.get("/api/wxsph/parse").status_code == 422


def test_wxsph_upstream_failures(client, monkeypatch, sph_env):
    monkeypatch.setattr(wxsph_route, "_post_json", lambda *a, **k: {"data": {}})
    r = client.get("/api/wxsph/parse", params={"url": SPH_URL + "/a"})
    assert r.status_code == 502 and "cookie" in r.json()["detail"]

    def feed_err(url, payload, headers, timeout=15):
        if url == wxsph_route.YUANBAO_PARSE_URL:
            return {"data": {"playable_url": "https://x/y?token=TK&eid=EID"}}
        return {"errCode": -1}
    monkeypatch.setattr(wxsph_route, "_post_json", feed_err)
    r = client.get("/api/wxsph/parse", params={"url": SPH_URL + "/b"})
    assert r.status_code == 502 and "errCode=-1" in r.json()["detail"]


def test_wxsph_post_json_network_error(monkeypatch):
    def boom(*a, **k):
        raise OSError("down")
    monkeypatch.setattr(wxsph_route.urllib.request, "urlopen", boom)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as ei:
        wxsph_route._post_json("https://x", {}, {})
    assert ei.value.status_code == 502


def test_wxsph_no_cookie(client, monkeypatch):
    monkeypatch.setattr(wxsph_route.settings, "wxsph_cookie", "", raising=False)
    import core.config
    monkeypatch.setattr(core.config.settings, "wxsph_cookie", "", raising=False)
    monkeypatch.delenv("WXSPH_COOKIE", raising=False)
    r = client.get("/api/wxsph/parse", params={"url": SPH_URL + "/nocookie"})
    assert r.status_code == 500


# ───────────── parse ─────────────

def test_parse_video_success(client, monkeypatch):
    async def fake(url):
        return VideoInfo(
            video_url="https://v/1.mp4", cover_url="https://c/1.jpg", title="标题", music_url="",
            images=[ImgInfo(url="https://i/1.jpg")], author=VideoAuthor(uid="1", name="作者", avatar="a"),
        )
    monkeypatch.setattr(parse_route, "parse_video_share_url", fake)
    r = client.get("/api/parse/video", params={"url": "https://h5.pipix.com/s/xxx"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["title"] == "标题" and data["video_url"] == "https://v/1.mp4"
    assert data["author"] == {"uid": "1", "name": "作者", "avatar": "a"}
    assert data["images"] == [{"url": "https://i/1.jpg", "live_photo_url": ""}]


def test_parse_video_missing_url(client):
    assert client.get("/api/parse/video").status_code == 422


@pytest.mark.parametrize("exc,status", [(ValueError("bad"), 400), (RuntimeError("down"), 500)])
def test_parse_video_errors(client, monkeypatch, exc, status):
    async def fake(url):
        raise exc
    monkeypatch.setattr(parse_route, "parse_video_share_url", fake)
    assert client.get("/api/parse/video", params={"url": "https://x.com/a"}).status_code == status


# ───────────── tools2 ─────────────

def test_answer_book(client):
    r = client.get("/api/tools2/answer", params={"question": "要不要"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["question"] == "要不要" and data["answer"] in extra2_route.ANSWERS


def test_answer_book_missing_question(client):
    assert client.get("/api/tools2/answer").status_code == 422


def test_food(client):
    r = client.get("/api/tools2/food")
    assert r.status_code == 200 and r.json()["data"]["food"] in extra2_route.FOODS


def _patch_httpx(monkeypatch, handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("verify", None)
        return real(*args, transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(extra2_route.httpx, "AsyncClient", factory)


def test_earthquake_success_list(client, monkeypatch):
    _patch_httpx(monkeypatch, lambda req: httpx.Response(200, json=[{"i": i} for i in range(20)]))
    r = client.get("/api/tools2/earthquake", params={"limit": 3})
    assert r.status_code == 200 and r.json()["data"] == [{"i": 0}, {"i": 1}, {"i": 2}]


def test_earthquake_success_dict(client, monkeypatch):
    _patch_httpx(monkeypatch, lambda req: httpx.Response(200, json={"no1": {"a": 1}, "items": list(range(20))}))
    r = client.get("/api/tools2/earthquake", params={"limit": 2})
    assert r.status_code == 200 and r.json()["data"]["items"] == [0, 1]


@pytest.mark.parametrize("limit", [0, 51])
def test_earthquake_limit_validation(client, limit):
    assert client.get("/api/tools2/earthquake", params={"limit": limit}).status_code == 422


def test_earthquake_upstream_non_json(client, monkeypatch):
    _patch_httpx(monkeypatch, lambda req: httpx.Response(200, text="<html>"))
    assert client.get("/api/tools2/earthquake").status_code == 502


def test_earthquake_upstream_http_error(client, monkeypatch):
    _patch_httpx(monkeypatch, lambda req: httpx.Response(503, json={"error": "maintenance"}))
    assert client.get("/api/tools2/earthquake").status_code == 502


def test_earthquake_network_error(client, monkeypatch):
    def handler(req):
        raise httpx.ConnectError("down")
    _patch_httpx(monkeypatch, handler)
    assert client.get("/api/tools2/earthquake").status_code == 502


def test_portal_catalog_matches_routes() -> None:
    """门户目录里的每个内置接口都要有真实路由，每个公开路由也都要出现在目录里。"""
    from core.database import API_CATALOG
    from core.routing import api_route_index
    from main import app

    paths, _ = api_route_index(app)
    catalog_paths = {item["path"] for item in API_CATALOG} | {"/api/douyin/parse"}
    public = {p for p in paths if p.startswith("/api/") and not p.startswith("/api/v1/") and "{slug}" not in p}
    assert sorted(p for p in catalog_paths if p not in paths) == []
    assert sorted(public - catalog_paths) == []

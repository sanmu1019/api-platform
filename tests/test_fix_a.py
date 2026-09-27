from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from core.database import init_db
from main import app

HEADERS = {"Api-Key": "test123"}


def _client() -> TestClient:
    init_db()
    return TestClient(app)


def test_bilibili_proxy_upstream_failure_returns_502(monkeypatch) -> None:
    async def fake_get(self, url, *args, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    resp = _client().get("/api/bilibili/proxy?bvid=BV1xx411c7mD&type=mp4", headers=HEADERS)
    assert resp.status_code == 502
    assert "ConnectError" in resp.json()["msg"]


def test_bilibili_proxy_rejects_bad_type() -> None:
    resp = _client().get("/api/bilibili/proxy?bvid=BV1xx411c7mD&type=flv", headers=HEADERS)
    assert resp.status_code == 422


def test_bilibili_proxy_forwards_range(monkeypatch) -> None:
    seen = {}

    async def fake_get(self, url, *args, **kwargs):
        if "view" in url:
            return httpx.Response(200, json={"data": {"cid": 1}})
        return httpx.Response(200, json={"data": {"durl": [{"url": "https://upos.bilivideo.com/v.mp4"}]}})

    async def fake_send(self, request, *args, **kwargs):
        seen["range"] = request.headers.get("range")
        return httpx.Response(
            206,
            headers={"Content-Range": "bytes 0-3/10", "Content-Length": "4", "Accept-Ranges": "bytes",
                     "Content-Type": "video/mp4"},
            content=b"abcd",
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
    monkeypatch.setattr("core.netsecurity.resolve_public_host", lambda host: (True, "", ["1.2.3.4"]))
    resp = _client().get(
        "/api/bilibili/proxy?bvid=BV1xx411c7mD", headers={**HEADERS, "Range": "bytes=0-3"}
    )
    assert resp.status_code == 206
    assert seen["range"] == "bytes=0-3"
    assert resp.headers["content-range"] == "bytes 0-3/10"
    assert resp.content == b"abcd"


def test_bilibili_proxy_rejects_private_stream_host(monkeypatch) -> None:
    async def fake_get(self, url, *args, **kwargs):
        if "view" in url:
            return httpx.Response(200, json={"data": {"cid": 1}})
        return httpx.Response(200, json={"data": {"durl": [{"url": "http://127.0.0.1/x"}]}})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    resp = _client().get("/api/bilibili/proxy?bvid=BV1xx411c7mD", headers=HEADERS)
    assert resp.status_code == 502


def test_music_limit_over_max_returns_422() -> None:
    client = _client()
    assert client.get("/api/music/qq/search?keyword=a&limit=31", headers=HEADERS).status_code == 422
    assert client.get("/api/music/kugou/search?keyword=a&limit=31", headers=HEADERS).status_code == 422


def test_joke_load_failure_returns_503(monkeypatch, tmp_path) -> None:
    from apis.joke import route as joke

    monkeypatch.setattr(joke, "DATA_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(joke, "_jokes", [])
    monkeypatch.setattr(joke, "_loaded", False)
    monkeypatch.setattr(joke, "_last_attempt", 0.0)
    calls = {"n": 0}
    real_open = open

    def counting_open(*args, **kwargs):
        calls["n"] += 1
        return real_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", counting_open)
    client = _client()
    calls["n"] = 0
    resp = client.get("/api/joke/random", headers=HEADERS)
    assert resp.status_code == 503
    assert resp.json()["code"] == 503
    # 失败后在重试间隔内不再重读文件
    before = calls["n"]
    assert client.get("/api/joke/random", headers=HEADERS).status_code == 503
    assert calls["n"] == before


def test_parse_internal_error_does_not_leak(monkeypatch) -> None:
    from apis.parse import route as parse

    async def boom(url):
        raise RuntimeError("secret-internal-detail")

    monkeypatch.setattr(parse, "parse_video_share_url", boom)
    resp = _client().get("/api/parse/video?url=https://example.com/x", headers=HEADERS)
    assert resp.status_code == 500
    assert "secret-internal-detail" not in resp.text


def test_bilibili_proxy_falls_back_to_backup_url(monkeypatch) -> None:
    tried = []

    async def fake_get(self, url, *args, **kwargs):
        if "view" in url:
            return httpx.Response(200, json={"data": {"cid": 1}})
        return httpx.Response(200, json={"data": {"durl": [
            {"url": "https://pcdn.example.cn:4483/v.mp4", "backup_url": ["https://upos.bilivideo.com/v.mp4"]}
        ]}})

    async def fake_send(self, request, *args, **kwargs):
        tried.append(request.url.host)
        if request.url.host == "pcdn.example.cn":
            raise httpx.ConnectError("unreachable")
        return httpx.Response(200, headers={"Content-Type": "video/mp4"}, content=b"ok")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "send", fake_send)
    monkeypatch.setattr("core.netsecurity.resolve_public_host", lambda host: (True, "", ["1.2.3.4"]))
    resp = _client().get("/api/bilibili/proxy?bvid=BV1xx411c7mD", headers=HEADERS)
    assert resp.status_code == 200
    assert tried == ["pcdn.example.cn", "upos.bilivideo.com"]


def test_qq_login_parses_cookie() -> None:
    from apis.music.route import _qq_login

    assert _qq_login("uin=o0012345; qqmusic_key=Q_H_L_abc") == ("12345", "Q_H_L_abc")
    assert _qq_login("uin=12345; qm_keyst=K") == ("12345", "K")
    assert _qq_login("uin=12345") == ("", "")


def test_qq_search_play_url_with_cookie(monkeypatch) -> None:
    from core.config import settings

    seen = {}

    async def fake_get(self, url, *args, **kwargs):
        if "client_search_cp" in url:
            return httpx.Response(200, json={"data": {"song": {"list": [
                {"songmid": "m1", "songname": "s", "singer": [{"name": "a"}], "albumname": "al"}]}}})
        seen["cookie"] = (kwargs.get("headers") or {}).get("Cookie")
        return httpx.Response(200, json={"req_0": {"code": 0, "data": {
            "sip": ["https://cdn.example/"], "midurlinfo": [{"songmid": "m1", "purl": "C400m1.m4a?x=1"}]}}})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(settings, "qqmusic_cookie", "uin=1; qqmusic_key=k")
    body = _client().get("/api/music/qq/search?keyword=x", headers=HEADERS).json()
    assert seen["cookie"] == "uin=1; qqmusic_key=k"
    assert body["data"][0]["play_url"] == "https://cdn.example/C400m1.m4a?x=1"
    assert "note" not in body


def test_qq_search_without_cookie_notes_missing(monkeypatch) -> None:
    from core.config import settings

    async def fake_get(self, url, *args, **kwargs):
        return httpx.Response(200, json={"data": {"song": {"list": [{"songmid": "m1", "songname": "s"}]}}})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(settings, "qqmusic_cookie", "")
    body = _client().get("/api/music/qq/search?keyword=x", headers=HEADERS).json()
    assert body["data"][0]["play_url"] == ""
    assert body["data"][0]["web_url"].endswith("/m1")
    assert "qqmusic_cookie" in body["note"]

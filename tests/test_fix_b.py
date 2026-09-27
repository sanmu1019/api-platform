from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from apis.exchange import route as exchange_route
from apis.hot import route as hot_route
from apis.weather import route as weather_route
from core.database import init_db
from core.ttlcache import TTLCache
from main import app

HEADERS = {"Api-Key": "test123"}


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.fixture()
def client():
    init_db()
    weather_route._cache.clear()
    exchange_route._cache.clear()
    hot_route._cache.clear()
    return TestClient(app)


def test_weather_city_not_found_404(client, monkeypatch):
    monkeypatch.setattr(weather_route.requests, "get", lambda *a, **k: _Resp({"results": []}))
    resp = client.get("/api/weather/current", params={"city": "不存在之城"}, headers=HEADERS)
    assert resp.status_code == 404


def test_weather_upstream_failure_502_hides_error(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret-internal-detail")

    monkeypatch.setattr(weather_route.requests, "get", boom)
    resp = client.get("/api/weather/current", params={"city": "北京"}, headers=HEADERS)
    assert resp.status_code == 502
    assert "secret-internal-detail" not in resp.text


def test_holiday_out_of_range_400(client):
    resp = client.get("/api/holiday/check", params={"date": "2099-01-01"}, headers=HEADERS)
    assert resp.status_code == 400
    assert "仅支持" in resp.text


def test_exchange_rate_unsupported_400(client, monkeypatch):
    monkeypatch.setattr(
        exchange_route.requests, "get",
        lambda *a, **k: _Resp({"amount": 1, "date": "2026-09-26", "rates": {}}),
    )
    resp = client.get("/api/exchange/rate", params={"from": "USD", "to": "XYZ"}, headers=HEADERS)
    assert resp.status_code == 400
    bad = client.get("/api/exchange/rate", params={"to": "1@3"}, headers=HEADERS)
    assert bad.status_code == 422


def test_ttlcache_maxsize_and_expiry(monkeypatch):
    cache = TTLCache(maxsize=3, ttl=10)
    for i in range(10):
        cache.set(i, i)
    assert len(cache) == 3
    assert cache.get(0) is None and cache.get(9) == 9

    now = [1000.0]
    monkeypatch.setattr("core.ttlcache.time.time", lambda: now[0])
    cache = TTLCache(maxsize=2, ttl=10)
    cache.set("a", 1)
    now[0] += 20
    assert cache.get("a") is None
    assert cache.get("a", allow_stale=True) == 1
    cache.set("b", 2)
    cache.set("c", 3)
    assert "a" not in cache and len(cache) == 2


def test_hot_cached_flag(client, monkeypatch):
    items = [{"rank": 1, "title": "t"}]
    monkeypatch.setitem(hot_route.PLATFORMS, "weibo", ("微博热搜", lambda: items))
    first = client.get("/api/hot/weibo", headers=HEADERS)
    second = client.get("/api/hot/weibo", headers=HEADERS)
    assert first.status_code == 200 and first.json()["data"]["cached"] is False
    assert second.json()["data"]["cached"] is True


def test_lunar_key_fields(client):
    resp = client.get("/api/lunar/day", params={"date": "2024-02-10"}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()["data"]
    for value in (
        data["solar"]["weekday"], data["lunar"]["year"], data["lunar"]["month"], data["lunar"]["day"],
        data["ganzhi"]["year"], data["ganzhi"]["day"], data["shengxiao"],
    ):
        assert value is not None
    assert data["shengxiao"] == "龙"

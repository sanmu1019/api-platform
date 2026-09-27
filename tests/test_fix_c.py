import random
import socket

import pytest
from fastapi.testclient import TestClient

from core.depends import verify_api_key
from main import app


@pytest.fixture()
def client():
    app.dependency_overrides[verify_api_key] = lambda: None
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


@pytest.mark.parametrize("num,expected", [
    ("0", "零元整"),
    ("1234.56", "壹仟贰佰叁拾肆元伍角陆分"),
    ("1.999", "贰元整"),
    ("100000000", "壹亿元整"),
    ("10.05", "壹拾元零伍分"),
])
def test_number_upper(client, num, expected):
    r = client.get("/api/extra/number/upper", params={"number": num})
    assert r.status_code == 200
    assert r.json()["data"]["upper"] == expected


@pytest.mark.parametrize("num", ["inf", "nan", "-5", "1e20", "abc", "1e16"])
def test_number_upper_invalid(client, num):
    assert client.get("/api/extra/number/upper", params={"number": num}).status_code == 400


def test_luck_keeps_global_random_state(client):
    state = random.getstate()
    r1 = client.get("/api/tools2/luck", params={"name": "张三"})
    assert random.getstate() == state
    r2 = client.get("/api/tools2/luck", params={"name": "张三"})
    assert r1.status_code == 200 and r1.json()["data"] == r2.json()["data"]


@pytest.mark.parametrize("code", ["", "   "])
def test_carplate_blank(client, code):
    assert client.get("/api/tools2/carplate", params={"code": code}).status_code in (400, 422)


def test_carplate_strip(client):
    r = client.get("/api/tools2/carplate", params={"code": "  京A"})
    assert r.status_code == 200 and r.json()["data"]["province"] == "北京"


def test_ping_caps_addresses(client, monkeypatch):
    import core.netsecurity as ns
    monkeypatch.setattr(ns, "resolve_public_host",
                        lambda h: (True, "", ["1.1.1.1", "1.1.1.2", "1.1.1.3", "1.1.1.4"]))
    tried = []

    def fake_conn(addr, timeout=None):
        tried.append(addr)
        raise OSError("refused")

    monkeypatch.setattr(socket, "create_connection", fake_conn)
    r = client.get("/api/extra/ping", params={"host": "example.com"})
    assert r.status_code == 200
    assert r.json()["data"]["reachable"] is False
    assert {a for a, _ in tried} <= {"1.1.1.1", "1.1.1.2"}
    assert len(tried) == 4

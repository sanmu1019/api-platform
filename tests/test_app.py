from fastapi.testclient import TestClient

from apis.douyin.service import DouyinParseError, extract_url
from core.config import Settings, settings
from core.database import init_db
from main import app


ADMIN_PATH = settings.normalized_admin_path


def test_home_and_portal_render() -> None:
    init_db()
    client = TestClient(app)

    home = client.get("/")
    assert home.status_code == 200
    assert "apiSearch" in home.text
    assert "/register" in home.text
    assert "/frontend/assets/app.js" in home.text
    assert "footerPhrase" in home.text

    portal = client.get("/portal/apis")
    assert portal.status_code == 200
    body = portal.json()["data"]
    assert body["apis"]
    assert body["site"]["site_name"]

    # 接口测试台：顶层 /test 与 /frontend/test.html 是同一份文件
    console = client.get("/test")
    assert console.status_code == 200
    assert "接口测试台" in console.text
    assert 'id="tpRunAll"' in console.text
    assert client.get("/frontend/test.html").text == console.text


def test_public_registration_and_core_endpoints() -> None:
    init_db()
    client = TestClient(app)

    page = client.get("/register")
    assert page.status_code == 200
    assert "registerKey" in page.text

    registered = client.post("/register/key", params={"name": "测试注册用户"})
    assert registered.status_code == 200
    key = registered.json()["data"]["key"]
    assert key.startswith("ak_")

    assert client.get("/api/demo", headers={"Api-Key": key}).status_code == 200
    assert client.get("/api/time", headers={"Api-Key": key}).status_code == 200
    assert client.get("/health").status_code == 200


def test_freeapi_collection() -> None:
    init_db()
    client = TestClient(app)
    headers = {"Api-Key": "test123"}

    yiyan = client.get("/api/yiyan", headers=headers)
    assert yiyan.status_code == 200
    assert yiyan.json()["data"]["text"]

    avatar = client.get("/api/avatar/random?seed=test", headers=headers)
    assert avatar.status_code == 200
    assert "url" in avatar.json()["data"]

    short = client.get("/api/short/hash?url=https://example.com", headers=headers)
    assert short.status_code == 200
    assert short.json()["data"]["short_code"]

    bad_short = client.get("/api/short/hash?url=ftp://example.com", headers=headers)
    assert bad_short.status_code == 400

    assert client.get("/api/bilibili/cover?bvid=BV1xx411c7mD", headers=headers).status_code == 200
    assert client.get("/api/bing/daily", headers=headers).status_code == 200


def test_tools_and_word_endpoints() -> None:
    init_db()
    client = TestClient(app)
    headers = {"Api-Key": "test123"}

    assert client.get("/api/word/random", headers=headers).status_code == 200
    assert client.get("/api/tool/timestamp", headers=headers).status_code == 200
    assert client.get("/api/tool/hash?text=abc&algorithm=sha256", headers=headers).status_code == 200
    assert client.get("/api/tool/base64?text=abc", headers=headers).json()["data"]["result"] == "YWJj"
    assert client.get("/api/tool/uuid?count=2", headers=headers).json()["data"]["count"] == 2
    assert len(client.get("/api/tool/password?length=12", headers=headers).json()["data"]["password"]) == 12
    assert client.get("/api/tool/color", headers=headers).json()["data"]["hex"].startswith("#")
    assert client.get("/api/tool/nickname", headers=headers).json()["data"]["nickname"]
    assert client.get("/api/image/placeholder?width=100&height=80&text=test", headers=headers).status_code == 200
    assert client.get("/api/image/qrcode?text=hello", headers=headers).status_code == 200


def test_spider_endpoints() -> None:
    init_db()
    client = TestClient(app)
    headers = {"Api-Key": "test123"}

    assert client.get("/api/history/today?date=05-21", headers=headers).json()["data"]["events"]
    assert client.get("/api/idiom/search?keyword=精", headers=headers).status_code == 200
    assert client.get("/api/poetry/tang?keyword=李白", headers=headers).status_code == 200


def test_versioned_aliases_and_validation_error_shape() -> None:
    init_db()
    client = TestClient(app)
    headers = {"Api-Key": "test123"}

    assert client.get("/api/v1/demo", headers=headers).status_code == 200
    assert client.get("/api/v1/tool/hash?text=abc", headers=headers).status_code == 200
    assert client.get("/api/v1/image/qrcode?text=hello", headers=headers).status_code == 200
    assert client.get("/api/v1/history/today", headers=headers).status_code == 200
    assert client.get("/api/version").json()["data"]["current"] == "v1"

    invalid = client.get("/api/tool/uuid?count=999", headers=headers)
    assert invalid.status_code == 422
    body = invalid.json()
    assert body["code"] == 422
    assert body["request_id"]


def test_admin_pages_and_endpoints() -> None:
    init_db()
    client = TestClient(app)

    home = client.get(f"{ADMIN_PATH}")
    assert home.status_code == 200
    assert "/static/admin.js" in home.text
    # 管理页外壳是**公开**服务的（只有数据接口校验 Admin-Token），
    # 所以页面源码里不能出现任何默认凭据 —— 否则等于把默认 Key
    # 直接交给未登录访问者（曾因 debugKey 的 value="test123" 踩过）。
    assert "test123" not in home.text
    assert "admin888" not in home.text

    assert client.get(f"{ADMIN_PATH}/apis").status_code == 401
    assert client.get(f"{ADMIN_PATH}/session").status_code == 401

    login = client.post(f"{ADMIN_PATH}/login", json={"token": "admin888"})
    assert login.status_code == 200
    assert "admin_token" in login.cookies

    assert client.get(f"{ADMIN_PATH}/apis").status_code == 200
    assert client.get(f"{ADMIN_PATH}/session").status_code == 200
    assert client.get(f"{ADMIN_PATH}/categories").status_code == 200
    assert client.get(f"{ADMIN_PATH}/route-check").status_code == 200
    assert client.get(f"{ADMIN_PATH}/access-logs").status_code == 200
    assert client.get(f"{ADMIN_PATH}/access-logs.csv").status_code == 200
    assert client.get(f"{ADMIN_PATH}/backup/database").status_code == 200

    script = client.get("/static/admin.js")
    assert script.status_code == 200
    assert "ADMIN_BASE" in script.text
    assert 'credentials: "same-origin"' in script.text
    assert "debugRequest" in script.text
    assert "/admin/login" in script.text


def test_admin_can_create_update_and_delete_custom_api() -> None:
    init_db()
    client = TestClient(app)
    headers = {"Admin-Token": "admin888"}

    client.delete(f"{ADMIN_PATH}/apis/hello", headers=headers)
    created = client.post(
        f"{ADMIN_PATH}/apis",
        headers=headers,
        params={
            "name": "hello",
            "path": "/api/hello",
            "title": "Hello 接口",
            "description": "后台创建的动态接口",
            "category": "自定义",
            "response_type": "json",
            "response_body": '{"hello":"world"}',
            "status_code": 201,
        },
    )
    assert created.status_code == 200

    response = client.get("/api/custom/hello", headers={"Api-Key": "test123"})
    assert response.status_code == 201
    assert response.json()["data"]["hello"] == "world"

    patched = client.patch(f"{ADMIN_PATH}/apis/hello", headers=headers, params={"enabled": False})
    assert patched.status_code == 200

    deleted = client.delete(f"{ADMIN_PATH}/apis/hello", headers=headers)
    assert deleted.status_code == 200


def test_admin_validates_custom_api_payload() -> None:
    init_db()
    client = TestClient(app)
    headers = {"Admin-Token": "admin888"}

    bad_path = client.post(
        f"{ADMIN_PATH}/apis",
        headers=headers,
        params={"name": "bad", "path": "/api/other/bad", "title": "Bad", "description": "bad path"},
    )
    assert bad_path.status_code == 400

    bad_json = client.post(
        f"{ADMIN_PATH}/apis",
        headers=headers,
        params={
            "name": "badjson",
            "path": "/api/badjson",
            "title": "Bad JSON",
            "description": "bad json",
            "response_type": "json",
            "response_body": "{bad",
        },
    )
    assert bad_json.status_code == 400

    bad_status = client.post(
        f"{ADMIN_PATH}/apis",
        headers=headers,
        params={
            "name": "badstatus",
            "path": "/api/badstatus",
            "title": "Bad Status",
            "description": "bad status",
            "status_code": 99,
        },
    )
    assert bad_status.status_code == 400


def test_api_key_state_and_quota_are_enforced() -> None:
    init_db()
    client = TestClient(app)
    headers = {"Admin-Token": "admin888"}

    client.delete(f"{ADMIN_PATH}/keys/limited", headers=headers)
    created = client.post(
        f"{ADMIN_PATH}/keys",
        headers=headers,
        params={"key": "limited", "name": "Limited", "quota_per_day": 1},
    )
    assert created.status_code == 200

    assert client.get("/api/demo", headers={"Api-Key": "limited"}).status_code == 200
    assert client.get("/api/demo", headers={"Api-Key": "limited"}).status_code == 429

    client.delete(f"{ADMIN_PATH}/keys/disabled", headers=headers)
    created = client.post(
        f"{ADMIN_PATH}/keys",
        headers=headers,
        params={"key": "disabled", "name": "Disabled"},
    )
    assert created.status_code == 200
    assert client.patch(f"{ADMIN_PATH}/keys/disabled", headers=headers, params={"enabled": False}).status_code == 200
    assert client.get("/api/demo", headers={"Api-Key": "disabled"}).status_code == 403

    assert client.get("/api/demo", headers={"Api-Key": "missing"}).status_code == 403


def test_dynamic_template_variables() -> None:
    init_db()
    client = TestClient(app)
    headers = {"Admin-Token": "admin888"}

    client.delete(f"{ADMIN_PATH}/apis/echo", headers=headers)
    created = client.post(
        f"{ADMIN_PATH}/apis",
        headers=headers,
        params={
            "name": "echo",
            "path": "/api/echo",
            "title": "Echo",
            "description": "echo",
            "category": "测试",
            "response_type": "json",
            "response_body": '{"name":"{{query.name}}","slug":"{{slug}}","method":"{{method}}"}',
        },
    )
    assert created.status_code == 200

    response = client.get("/api/custom/echo?name=alice", headers={"Api-Key": "test123"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "alice"
    assert data["slug"] == "echo"
    assert data["method"] == "GET"

    client.delete(f"{ADMIN_PATH}/apis/echo", headers=headers)


def test_doc_frontend_has_online_debug_helpers() -> None:
    client = TestClient(app)
    script = client.get("/frontend/assets/doc.js")
    assert script.status_code == 200
    assert "fillPathParams" in script.text
    assert "data-param-in" in script.text
    assert "idiom_search" in script.text
    assert "keyword=%E7%B2%BE" in script.text
    assert "poetry_tang" in script.text

    # history/today 的 date 示例值必须是动态的"今天"。
    # 曾经写死成 date=05-21，导致「在线调试」默认演示一个过去的日期，
    # 与接口名 today 自相矛盾（9 月点开调试却看到 5 月 21 日的事件）。
    assert "todayMMDD" in script.text
    assert "date=05-21" not in script.text


def test_history_today_defaults_to_server_date() -> None:
    """不传 date 时应取当天，且与显式传当天等价。"""
    from datetime import date

    init_db()
    client = TestClient(app)
    today = date.today().strftime("%m-%d")

    default = client.get("/api/history/today").json()["data"]
    explicit = client.get(f"/api/history/today?date={today}").json()["data"]
    assert default["date"] == today
    assert default["events"] == explicit["events"]
    assert default["covered_dates"] >= 366

    # 格式非法要挡住，而不是静默当成今天
    assert client.get("/api/history/today?date=5-2").status_code == 422


def test_history_corpus_has_no_blocked_entries() -> None:
    """语料里不得残留过滤词表命中的内容。

    词表本身是敏感词清单，**不入库**（见 .gitignore），所以本地缺它时跳过 ——
    别人克隆仓库后不会因为文件缺失而失败。这条守的是"数据被手工改回去"这类
    回归：语料一旦混进不该展示的条目，这里会红。
    """
    import json
    import pathlib

    import pytest

    data_dir = pathlib.Path(__file__).resolve().parents[1] / "apis" / "data"
    blocklist = data_dir / "history_today.blocklist.txt"
    if not blocklist.exists():
        pytest.skip("未找到 history_today.blocklist.txt（词表不入库），跳过")

    subs: list[str] = []
    combos: list[tuple[str, ...]] = []
    for raw in blocklist.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("+"):
            combos.append(tuple(p for p in line.split("+") if p))
        else:
            subs.append(line)

    data = json.loads((data_dir / "history_today.json").read_text(encoding="utf-8"))
    # 日期键必须保持完整，否则 /api/history/today 的 covered_dates 会变
    assert len(data) == 366

    bad = [
        sub
        for events in data.values()
        for entry in events
        for sub in entry.split("${{delimiter}}")
        if any(w in sub for w in subs) or any(all(w in sub for w in c) for c in combos)
    ]
    assert bad == [], f"语料残留 {len(bad)} 条未过滤内容"


def test_footer_phrase_loader_present() -> None:
    client = TestClient(app)
    script = client.get("/frontend/assets/app.js")
    assert script.status_code == 200
    assert "loadFooterPhrase" in script.text
    assert "/api/yiyan" in script.text


def test_security_headers_and_settings_validation() -> None:
    init_db()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Referrer-Policy" in response.headers

    weak = Settings(environment="production", admin_token="admin888", default_api_keys="test123:测试")
    try:
        weak.validate_public_security()
    except RuntimeError as exc:
        assert "ADMIN_TOKEN" in str(exc)
    else:
        raise AssertionError("production weak admin token should be rejected")

    strong = Settings(environment="production", admin_token="strong-admin-token-123", default_api_keys="strong-api-key:用户")
    strong.validate_public_security()


def test_douyin_url_extraction_and_mocking(monkeypatch) -> None:
    assert extract_url("分享一个 https://v.douyin.com/abcd1234/ 太好用了") == "https://v.douyin.com/abcd1234"

    init_db()
    client = TestClient(app)

    monkeypatch.setattr(
        "apis.douyin.route.parse_douyin",
        lambda text, timeout=6.0, debug=False: {"input": text, "timeout": timeout, "debug": debug, "ok": True},
    )
    response = client.get(
        "/api/douyin/parse",
        params={"url": "https://v.douyin.com/mock/", "timeout": 3, "debug": True},
        headers={"Api-Key": "test123"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is True

    monkeypatch.setattr(
        "apis.douyin.route.probe_douyin",
        lambda text, timeout=5.0: {"input": text, "final_url": "https://www.douyin.com/video/1"},
    )
    probe = client.get(
        "/api/douyin/parse",
        params={"url": "https://v.douyin.com/mock/", "probe": True},
        headers={"Api-Key": "test123"},
    )
    assert probe.status_code == 200
    assert probe.json()["data"]["final_url"].endswith("/video/1")

    def fail_parse(text, timeout=6.0, debug=False):
        raise DouyinParseError("解析失败", {"stage": "unit-test"})

    monkeypatch.setattr("apis.douyin.route.parse_douyin", fail_parse)
    failed = client.get(
        "/api/douyin/parse",
        params={"url": "https://v.douyin.com/mock/", "debug": True},
        headers={"Api-Key": "test123"},
    )
    assert failed.status_code == 400
    assert failed.json()["detail"]["debug"]["stage"] == "unit-test"

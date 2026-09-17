from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import urllib.parse


BASE = "http://127.0.0.1:8000"
checks: list[tuple[str, bool, str]] = []


def safe(text: object) -> str:
    return str(text).encode("gbk", errors="replace").decode("gbk")


def curl(path: str, method: str = "GET", data: dict | None = None):
    url = path if path.startswith("http") else BASE + path
    cmd = ["curl.exe", "-sS", "-X", method, url]
    if data is not None:
        cmd.extend(["-H", "Content-Type: application/json", "--data", json.dumps(data, ensure_ascii=False)])
    p = subprocess.run(cmd, capture_output=True, timeout=30)
    stdout = p.stdout.decode("utf-8", errors="replace")
    stderr = p.stderr.decode("utf-8", errors="replace")
    return p.returncode, stdout, stderr


def curl_json(path: str, method: str = "GET", data: dict | None = None):
    code, out, err = curl(path, method=method, data=data)
    try:
        body = json.loads(out)
    except Exception:
        body = None
    return code, body, out, err


def add(name: str, ok: bool, detail: object = ""):
    checks.append((name, bool(ok), str(detail)))
    print(("PASS" if ok else "FAIL"), name, safe(detail))


code, body, *_ = curl_json("/health")
add("health", code == 0 and body and body.get("status") == "ok", body)

code, body, *_ = curl_json("/api/demo")
add("demo_no_auth", body and body.get("code") == 200 and body.get("data"), body)

code, body, *_ = curl_json("/api/ip")
add("ip_no_auth", body and body.get("data", {}).get("ip"), body)

code, body, *_ = curl_json("/api/time")
add("time_no_auth", body and {"timestamp", "datetime"} <= set(body.get("data", {}).keys()), body)

code, body, *_ = curl_json("/api/phone/13800138000")
data = body.get("data", {}) if body else {}
add("phone_no_auth", body and data.get("phone") == "13800138000" and data.get("isp"), body)

code, body, *_ = curl_json("/api/yiyan")
add("yiyan_no_auth", body and bool(body.get("data")), body)

code, body, *_ = curl_json("/api/short/hash?url=https://example.com")
data = body.get("data", {}) if body else {}
add("short_hash", body and data.get("url") == "https://example.com" and data.get("short_code"), body)

code, body, *_ = curl_json("/api/tool/hash?text=abc&algorithm=sha256")
add("hash_sha256", body and body.get("data", {}).get("hash") == hashlib.sha256(b"abc").hexdigest(), body)

code, body, *_ = curl_json("/api/tool/base64?text=abc")
add("base64", body and body.get("data", {}).get("result") == "YWJj", body)

code, body, *_ = curl_json("/api/tool/uuid?count=2")
items = body.get("data", {}).get("items", []) if body else []
add("uuid_count", len(items) == 2 and all(re.match(r"^[0-9a-f-]{36}$", x) for x in items), body)

code, body, *_ = curl_json("/api/news/list?type=0&page=1&size=2")
news = body.get("data", {}).get("items", []) if body else []
add("news_list", len(news) == 2 and news[0].get("postid"), body)

if news:
    postid = urllib.parse.quote(news[0]["postid"])
    code, body, *_ = curl_json(f"/api/news/detail?postid={postid}")
    add("news_detail", body and body.get("data", {}).get("postid") == news[0]["postid"], body)

code, body, *_ = curl_json("/api/video/list")
videos = body.get("data", {}).get("items", []) if body else []
add("video_list", len(videos) > 0 and videos[0].get("vid"), body)

code, body, *_ = curl_json("/api/joke/random?count=2")
jokes = body.get("data", []) if body else []
if isinstance(jokes, dict):
    jokes = jokes.get("items", [])
add("joke_count", len(jokes) == 2, body)

code, body, *_ = curl_json("/api/idiom/search?keyword=%E7%B2%BE")
add("idiom_search", body and bool(body.get("data")), body)

code, body, *_ = curl_json("/portal/apis")
catalog = body.get("data", {}).get("apis", []) if body else []
add("portal_catalog", len(catalog) >= 20, f"count={len(catalog)}")

code, body, *_ = curl_json("/manage-api/apis")
add("admin_apis_no_auth", body and body.get("code") == 200 and isinstance(body.get("data"), list), body)

code, body, *_ = curl_json(
    "/api/douyin/parse",
    method="POST",
    data={"url": "https://v.douyin.com/-esXsdHPzp0/", "probe": True, "timeout": 6},
)
add("douyin_probe_no_auth", body and body.get("code") == 200 and "final_url" in body.get("data", {}), body)

failed = [x for x in checks if not x[1]]
print(f"\nSUMMARY {len(checks)-len(failed)}/{len(checks)} passed")
if failed:
    for name, _, detail in failed:
        print("FAILED", name, safe(detail))
    sys.exit(1)

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import init_db
from main import app


CASES = [
    ("GET", "/api/demo"),
    ("GET", "/api/ip"),
    ("GET", "/api/time"),
    ("GET", "/api/phone/13800138000"),
    ("GET", "/api/word/random"),
    ("GET", "/api/yiyan"),
    ("GET", "/api/avatar/random?seed=test"),
    ("GET", "/api/short/hash?url=https://example.com"),
    ("GET", "/api/bilibili/cover?bvid=BV1xx411c7mD"),
    ("GET", "/api/bing/daily"),
    ("GET", "/api/tool/timestamp"),
    ("GET", "/api/tool/hash?text=abc&algorithm=sha256"),
    ("GET", "/api/tool/base64?text=abc"),
    ("GET", "/api/tool/uuid?count=2"),
    ("GET", "/api/tool/password?length=12"),
    ("GET", "/api/tool/color"),
    ("GET", "/api/tool/nickname"),
    ("GET", "/api/image/placeholder?width=100&height=80&text=test"),
    ("GET", "/api/image/qrcode?text=hello"),
]


def main() -> int:
    init_db()
    client = TestClient(app)
    headers = {}
    failed = 0
    for method, path in CASES:
        response = client.request(method, path, headers=headers)
        ok = 200 <= response.status_code < 300
        print(f"{'OK' if ok else 'FAIL'} {response.status_code:>3} {method} {path}")
        if not ok:
            failed += 1
            print(response.text[:500])
    return failed


if __name__ == "__main__":
    raise SystemExit(main())


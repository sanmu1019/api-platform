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
    ("history_today", "/api/history/today?date=05-21", lambda d: isinstance(d.get("events"), list) and len(d["events"]) >= 1),
    ("idiom_search", "/api/idiom/search?keyword=%E7%B2%BE", lambda d: isinstance(d, list) and len(d) >= 1),
    ("poetry_tang", "/api/poetry/tang?keyword=%E6%9D%8E%E7%99%BD", lambda d: isinstance(d, list) and len(d) >= 1),
    ("hot_platforms", "/api/hot/platforms", lambda d: isinstance(d, list) and len(d) >= 1),
]


def main() -> int:
    init_db()
    client = TestClient(app)
    headers = {"Api-Key": "test123"}
    failed = []
    for name, path, check in CASES:
        response = client.get(path, headers=headers)
        body = response.json()
        data = body.get("data") if isinstance(body, dict) else None
        usable = response.status_code == 200 and check(data)
        print(f"{name}: status={response.status_code}, usable={usable}, path={path}")
        if not usable:
            failed.append((name, response.status_code, body))
    if failed:
        print("FAILED:")
        for item in failed:
            print(item)
        return 1
    print(f"ALL_USABLE {len(CASES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

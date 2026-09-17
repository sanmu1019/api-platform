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
    ("news_categories", "/api/news/categories", lambda d: isinstance(d, list) and len(d) >= 1),
    ("news_list", "/api/news/list?type=0&page=1&size=2", lambda d: isinstance(d, dict) and len(d.get("items", [])) == 2),
    ("news_detail", "/api/news/detail?postid=N20260521001", lambda d: d.get("postid") == "N20260521001"),
    ("video_list", "/api/video/list", lambda d: isinstance(d, dict) and len(d.get("items", [])) >= 1),
    ("video_detail", "/api/video/detail?vid=V10001", lambda d: d.get("vid") == "V10001" and "mp4_url" in d),
    ("joke_random", "/api/joke/random?count=2", lambda d: isinstance(d, list) and len(d) == 2),
    ("picture_cosplay", "/api/picture/cosplay?size=2", lambda d: isinstance(d, dict) and len(d.get("items", [])) == 2),
    ("history_today", "/api/history/today?date=05-21", lambda d: isinstance(d.get("events"), list) and len(d["events"]) >= 1),
    ("idiom_search", "/api/idiom/search?keyword=%E7%B2%BE", lambda d: isinstance(d, list) and len(d) >= 1),
    ("poetry_tang", "/api/poetry/tang?keyword=%E6%9D%8E%E7%99%BD", lambda d: isinstance(d, list) and len(d) >= 1),
    ("university_search", "/api/university/search?province=%E5%8C%97%E4%BA%AC", lambda d: isinstance(d, list) and len(d) >= 1),
]


def main() -> int:
    init_db()
    client = TestClient(app)
    headers = {}
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


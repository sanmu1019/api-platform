from __future__ import annotations

import logging
import random
from datetime import date

from fastapi import APIRouter, Depends, Query

from apis.data_loader import load_json
from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["spider"], dependencies=[Depends(verify_api_key)])

SPIDER_DATA = load_json("spider.json")


# 下面三个语料由 tools/build_datasets.py 生成，合计约 9 MB。
# 它们走函数内懒加载而不是模块级常量：load_json 自带 lru_cache，
# 首次请求时读盘、之后命中缓存；若在 import 时读，启动就要多花几秒。
def _load_or_fallback(name: str, fallback_key: str):
    try:
        return load_json(name)
    except (OSError, ValueError):
        logger.warning(
            "语料 %s 不可用，回退到 spider.json[%s]；请运行 tools/build_datasets.py",
            name, fallback_key,
        )
        return SPIDER_DATA[fallback_key]


def _poetry() -> list[dict]:
    return _load_or_fallback("poetry_tang.json", "poetry")


def _idioms() -> list[dict]:
    return _load_or_fallback("idioms.json", "idioms")


def _history() -> dict[str, list[str]]:
    return _load_or_fallback("history_today.json", "history")


@router.get("/history/today", name="history_today")
def history_today(date_str: str | None = Query(None, alias="date", pattern=r"^\d{2}-\d{2}$")) -> dict:
    history = _history()
    key = date_str or date.today().strftime("%m-%d")
    events = history.get(key) or []
    return {
        "code": 200,
        "msg": "success" if events else "no data",
        "data": {
            "date": key,
            "events": events,
            "available": bool(events),
            "covered_dates": len(history),
            "source": "local",
        },
    }


@router.get("/idiom/search", name="idiom_search")
def idiom_search(
    keyword: str = Query(..., min_length=1, max_length=20),
    limit: int = Query(20, ge=1, le=200),
) -> dict:
    """按成语本身检索（词条 / 拼音），不检索释义。"""
    idioms = _idioms()
    kw = keyword.strip()
    kw_lower = kw.lower()

    exact: list[dict] = []
    partial: list[dict] = []
    for item in idioms:
        if item["word"] == kw:
            exact.append(item)
        elif kw in item["word"] or kw_lower in item["pinyin"]:
            partial.append(item)

    rows = exact + partial
    return {"code": 200, "msg": "success", "data": rows[:limit],
            "matched": len(rows), "exact": bool(exact), "pool_size": len(idioms)}


@router.get("/poetry/tang", name="poetry_tang")
def poetry_tang(keyword: str | None = None, count: int = Query(1, ge=1, le=10)) -> dict:
    poetry = _poetry()
    matched_rows = (
        [item for item in poetry
         if keyword in item["title"] or keyword in item["author"] or keyword in item["content"]]
        if keyword else list(poetry)
    )
    pool = matched_rows or poetry
    picked = random.sample(pool, k=min(count, len(pool)))
    return {"code": 200, "msg": "success", "data": picked,
            "pool_size": len(poetry), "matched": len(matched_rows),
            "fallback": bool(keyword) and not matched_rows}

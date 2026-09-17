from __future__ import annotations

import logging
import random
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from apis.data_loader import load_json
from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["spider"], dependencies=[Depends(verify_api_key)])

SPIDER_DATA = load_json("spider.json")
NEWS_CATEGORIES = SPIDER_DATA["news_categories"]
NEWS_SEEDS = SPIDER_DATA["news_seeds"]
VIDEOS = SPIDER_DATA["videos"]


# 下面三个语料由 tools/build_datasets.py 生成，合计约 9 MB。
# 它们走函数内懒加载而不是模块级常量：load_json 自带 lru_cache，
# 首次请求时读盘、之后命中缓存；若在 import 时读，启动就要多花几秒。
#
# 没跑过构建脚本（或文件被删）时不能直接 500 —— 退回 spider.json 里那份
# 小样本，接口仍然可用，只是 pool_size 会明显偏小，一眼能看出该补数据了。
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


def _paginate(items: list[dict], page: int, size: int) -> dict:
    start = (page - 1) * size
    end = start + size
    return {"page": page, "size": size, "total": len(items), "items": items[start:end]}


@router.get("/news/categories", name="news_categories")
def news_categories() -> dict:
    return {"code": 200, "msg": "success", "data": NEWS_CATEGORIES}


@router.get("/news/list", name="news_list")
def news_list(type: int = Query(0, ge=0, le=7), page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=50)) -> dict:
    category = NEWS_CATEGORIES[type]
    rows = [
        {
            "postid": f"{item[0]}-{type}-{page}",
            "title": f"{category['name']}：{item[1]}",
            "source": item[2],
            "digest": item[3],
            "ptime": f"{date.today().isoformat()} 09:{idx:02d}:00",
        }
        for idx, item in enumerate(NEWS_SEEDS, start=1)
    ]
    # 内容由本地种子拼装，不是真实数据源
    return {"code": 200, "msg": "success",
            "data": {**_paginate(rows, page, size), "sample": True}}


@router.get("/news/detail", name="news_detail")
def news_detail(postid: str = Query(..., min_length=3)) -> dict:
    """按 postid 取详情。

    原实现完全忽略入参，任何 postid 都返回同一段"本地新闻详情示例"，
    连 zzz999 这种不存在的 id 也返回 200 —— 而同文件的 video_detail
    对未知 vid 是老老实实 404 的，两边行为不一致。
    """
    seed = next((item for item in NEWS_SEEDS if postid.startswith(str(item[0]))), None)
    if seed is None:
        raise HTTPException(status_code=404, detail="新闻不存在")

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "postid": postid,
            "title": seed[1],
            "source": seed[2],
            "digest": seed[3],
            "body": seed[3],
            "images": ["https://picsum.photos/seed/news-detail/800/450"],
            "sample": True,
        },
    }


@router.get("/video/list", name="video_list")
def video_list(type: str = "全部", page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=50)) -> dict:
    rows = [item for item in VIDEOS if type == "全部" or item["type"] == type]
    # 内容由本地种子拼装，不是真实数据源
    return {"code": 200, "msg": "success",
            "data": {**_paginate(rows, page, size), "sample": True}}


@router.get("/video/detail", name="video_detail")
def video_detail(vid: str = Query(..., min_length=3)) -> dict:
    row = next((item for item in VIDEOS if item["vid"] == vid), None)
    if not row:
        raise HTTPException(status_code=404, detail="视频不存在")
    return {
        "code": 200,
        "msg": "success",
        "data": {
            **row,
            "mp4_url": f"https://example.com/videos/{vid}.mp4",
            "m3u8_url": f"https://example.com/videos/{vid}/index.m3u8",
        },
    }


@router.get("/picture/cosplay", name="picture_cosplay")
def picture_cosplay(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=30)) -> dict:
    rows = [
        {
            "setid": f"P{page}{idx:03d}",
            "setname": f"创意相册 {idx}",
            "desc": "本地生成的相册数据，结构参考图片相册爬虫接口。",
            "cover": f"https://picsum.photos/seed/cosplay-{page}-{idx}/640/420",
            "pics": [f"https://picsum.photos/seed/cosplay-{page}-{idx}-{n}/900/600" for n in range(1, 4)],
        }
        for idx in range(1, size + 1)
    ]
    # 图片是 picsum 占位图、文案是本地生成的，不是真实相册数据
    return {"code": 200, "msg": "success",
            "data": {"page": page, "size": size, "items": rows, "sample": True}}


@router.get("/history/today", name="history_today")
def history_today(date_str: str | None = Query(None, alias="date", pattern=r"^\d{2}-\d{2}$")) -> dict:
    history = _history()
    key = date_str or date.today().strftime("%m-%d")
    events = history.get(key) or []
    # 原来查不到时往 events 里塞一句"暂无本地历史数据…"，调用方取 events[0]
    # 展示出来就成了一条假的历史事件。语料后来补到了全年 366 天（31622 条），
    # 但只要传一个语料里没有的日期（或格式合法却不存在的 02-30），仍会走到
    # 这个分支 —— 所以仍然返回空列表 + 显式标志位，不塞占位文案。
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
    """按成语本身检索（词条 / 拼音），**不检索释义**。

    成语检索是"查词"，不是全文检索。原先把 `explain` 也纳入匹配，于是
    搜「无懈可击」除了它自己，还会带出「滴水不漏」「汤池铁城」—— 仅仅因为
    它们的释义里提到了这个词。搜「精」更夸张：102 条词条命中，却因为释义
    含「精」多带出 507 条噪音，信号被淹没。

    词条完全相同的结果排在最前，并用 `exact` 告诉调用方"这就是那个成语"。
    """
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
    # 语料涨到三万条后，"一"这类常见字能命中上千条，全量返回会是几 MB 的响应
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
    # 关键词 0 命中时退回全量随机，保证接口总是有内容可返回；
    # 但 matched 必须如实报告「命中了几条」—— 原先命中 0 条时 rows 被重置成全量，
    # matched 于是返回语料规模（6306），调用方会误以为关键词命中了一切。
    pool = matched_rows or poetry
    # 这里原本是 rows[:count]，等于每次都返回命中集的头几首。
    # 线上 poetry_tang 被调用 277 次，全部返回《静夜思》。
    picked = random.sample(pool, k=min(count, len(pool)))
    # pool_size 让调用方看得见语料规模：不暴露的话，"随机一首"听起来
    # 像有海量诗库，实际只在 len(POETRY) 首里挑。
    return {"code": 200, "msg": "success", "data": picked,
            "pool_size": len(poetry), "matched": len(matched_rows),
            # 关键词没命中却仍返回了内容时，明确告诉调用方这是回退结果
            "fallback": bool(keyword) and not matched_rows}

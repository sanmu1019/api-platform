"""梅花易数起卦。

从 `E:\\wxbot-ipad` 的 meihuayi 插件移植：`engine.py` 原样复制，
这里只补一层 FastAPI 包装。

选它移植是因为在一堆插件里它最"干净"——纯本地计算，不依赖网络、
不依赖 AI、不依赖微信，`engine.py` 只用标准库。同样的输入永远得到同样的卦，
很适合放进接口平台。
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key

from .engine import PlumBlossom

router = APIRouter(prefix="/api/divination", tags=["divination"], dependencies=[Depends(verify_api_key)])

_engine = PlumBlossom()

DISCLAIMER = "结果仅作传统文化娱乐参考，不构成任何建议"


def _shape(result: dict, question: str) -> dict:
    """把引擎返回的扁平字典整理成分层结构，顺带给出可直接展示的文本。"""
    ben = result.get("ben") or {}
    return {
        "question": question,
        "method": result.get("method", ""),
        "time": {
            "year": result.get("year"),
            "month": result.get("month2"),
            "day": result.get("day"),
            "hour": result.get("hour"),
            "ganzhi": result.get("ganzhi", {}),
        },
        "hexagrams": {
            "ben": result.get("ben", {}),
            "hu": result.get("hu", {}),
            "bian": result.get("bian", {}),
        },
        "analysis": {
            "body_gua": result.get("body_gua_name", ""),
            "use_gua": result.get("use_gua_name", ""),
            "body_element": result.get("body_elem", ""),
            "use_element": result.get("use_elem", ""),
            "relation": result.get("relation", ""),
            "fortune": result.get("fortune", ""),
            # 动爻是 1~6 的爻位，决定变卦与体用。原先这里装的是「应期」
            # （upper + lower + 时支序，值域 3~28），字段名与内容不符，
            # 而真正的动爻（result['ben']['mv']）从未出现在响应里。
            # 应期另立 yingqi 字段，两边各归其位。
            "moving_line": ben.get("mv"),
            "yingqi": result.get("yingqi"),
        },
        "text": _engine.format_output(result, question),
        "disclaimer": DISCLAIMER,
    }


@router.get("/plum", name="divination_plum")
def plum_time(
    question: str = Query("", max_length=100, description="所问之事，仅用于回显"),
    year: int | None = Query(None, ge=1900, le=2200),
    month: int | None = Query(None, ge=1, le=12),
    day: int | None = Query(None, ge=1, le=31),
    hour: int | None = Query(None, ge=0, le=23),
) -> dict:
    """时间起卦。不传时间则用服务器当前时间。"""
    now = datetime.now()
    y = year if year is not None else now.year
    m = month if month is not None else now.month
    d = day if day is not None else now.day
    h = hour if hour is not None else now.hour

    # 逐项范围校验拦不住 2 月 30 日这种组合：引擎只做算术不查日历，
    # 会照样算出一卦来 —— 静默给出错误结果比报错更糟。
    try:
        datetime(y, m, d, h)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"日期不存在：{y}-{m}-{d}") from exc

    try:
        result = _engine.time_divination(y, m, d, h)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"起卦失败：{exc}") from exc
    return {"code": 200, "msg": "success", "data": _shape(result, question)}


@router.get("/number", name="divination_number")
def plum_number(
    number: int = Query(..., ge=100, le=999, description="三位数字，如 258"),
    question: str = Query("", max_length=100),
    month: int | None = Query(None, ge=1, le=12, description="不传则用当前月"),
    hour: int | None = Query(None, ge=0, le=23, description="不传则用当前小时；动爻取决于时辰，传了才能复现同一卦"),
) -> dict:
    """数字起卦。引擎要求三位数，范围校验交给 FastAPI。"""
    try:
        result = _engine.number_divination(number, month, hour)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"code": 200, "msg": "success", "data": _shape(result, question)}

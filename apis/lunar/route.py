from __future__ import annotations

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from lunar_python import Solar

from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lunar", tags=["lunar"], dependencies=[Depends(verify_api_key)])


def _parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {s}，应为 YYYY-MM-DD")


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


@router.get("/day", name="lunar_day")
def lunar_day(date_str: str = Query(..., alias="date", pattern=r"^\d{4}-\d{2}-\d{2}$")) -> dict:
    """万年历/老黄历：公历转农历，含干支、生肖、节气、宜忌、吉神方位等。

    date: 公历日期 YYYY-MM-DD
    """
    d = _parse_date(date_str)
    solar = Solar.fromYmd(d.year, d.month, d.day)
    lunar = solar.getLunar()

    # 吉神方位
    lucky = {}
    for direction in ["喜神", "福神", "财神", "阳贵神", "阴贵神"]:
        val = _safe(lambda dir_=direction: lunar.getPositionLuck(dir_))
        if val:
            lucky[direction] = val

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "solar": {
                "date": d.isoformat(),
                "weekday": _safe(lambda: lunar.getWeekInChinese()),
            },
            "lunar": {
                "year": _safe(lambda: lunar.getYearInChinese()),
                "month": _safe(lambda: lunar.getMonthInChinese()),
                "day": _safe(lambda: lunar.getDayInChinese()),
                "full": _safe(lambda: lunar.toString()),
            },
            "ganzhi": {
                "year": _safe(lambda: lunar.getYearInGanZhi()),
                "month": _safe(lambda: lunar.getMonthInGanZhi()),
                "day": _safe(lambda: lunar.getDayInGanZhi()),
                "hour": _safe(lambda: lunar.getTimeInGanZhi()),
            },
            "shengxiao": _safe(lambda: lunar.getYearShengXiao()),
            "jieqi": {
                "current": _safe(lambda: lunar.getJieQi()),
            },
            "yi": _safe(lambda: lunar.getDayYi(), []),
            "ji": _safe(lambda: lunar.getDayJi(), []),
            "pengzu": {
                "gan": _safe(lambda: lunar.getPengZuGan()),
                "zhi": _safe(lambda: lunar.getPengZuZhi()),
            },
            "chongsha": {
                "chong": _safe(lambda: lunar.getDayChongDesc()),
                "sha": _safe(lambda: lunar.getDaySha()),
            },
            "nayin": {
                "year": _safe(lambda: lunar.getYearNaYin()),
                "month": _safe(lambda: lunar.getMonthNaYin()),
                "day": _safe(lambda: lunar.getDayNaYin()),
            },
            "lucky_directions": lucky,
            "taishen": _safe(lambda: lunar.getDayPositionTai()),
            "xingxiu": {
                "name": _safe(lambda: lunar.getXiu()),
                "animal": _safe(lambda: lunar.getAnimal()),
                "luck": _safe(lambda: lunar.getXiuLuck()),
            },
        },
        "source": "lunar-python (纯算法，零依赖)",
    }

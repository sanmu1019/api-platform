from __future__ import annotations

import logging
from datetime import date, datetime

import chinese_calendar as cn_calendar
from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/holiday", tags=["holiday"], dependencies=[Depends(verify_api_key)])


def _parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {s}，应为 YYYY-MM-DD")


@router.get("/check", name="holiday_check")
def holiday_check(date_str: str = Query(..., alias="date", pattern=r"^\d{4}-\d{2}-\d{2}$")) -> dict:
    """查询指定日期是否为工作日/节假日。

    date: 日期 YYYY-MM-DD
    """
    d = _parse_date(date_str)
    is_workday = cn_calendar.is_workday(d)
    is_holiday = cn_calendar.is_holiday(d)
    is_in_lieu = cn_calendar.is_in_lieu(d)
    holiday_detail = cn_calendar.get_holiday_detail(d)

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "date": d.isoformat(),
            "weekday": d.strftime("%A"),
            "is_workday": is_workday,
            "is_holiday": is_holiday,
            "is_in_lieu": is_in_lieu,
            "holiday_name": holiday_detail[1] if holiday_detail[0] else None,
        },
        "source": "chinesecalendar (国务院公告)",
    }

from datetime import datetime
import time

from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key

router = APIRouter(prefix="/api", tags=["time"], dependencies=[Depends(verify_api_key)])


@router.get("/time", name="time")
def get_time(value: int | None = Query(None, description="Unix 时间戳，不传则返回当前时间")) -> dict:
    if value is None:
        ts = int(time.time())
        dt = datetime.now()
    else:
        ts = int(value)
        try:
            dt = datetime.fromtimestamp(ts)
        except (OSError, OverflowError, ValueError):
            raise HTTPException(status_code=400, detail="timestamp 超出可表示范围") from None
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "timestamp": ts,
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

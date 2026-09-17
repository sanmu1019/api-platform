from datetime import datetime
import time

from fastapi import APIRouter, Depends

from core.depends import verify_api_key

router = APIRouter(prefix="/api", tags=["time"], dependencies=[Depends(verify_api_key)])


@router.get("/time", name="time")
def get_time() -> dict:
    now = datetime.now()
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "timestamp": int(time.time()),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

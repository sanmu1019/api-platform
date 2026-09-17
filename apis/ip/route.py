from fastapi import APIRouter, Depends, Request

from core.depends import verify_api_key

router = APIRouter(prefix="/api", tags=["ip"], dependencies=[Depends(verify_api_key)])


@router.get("/ip", name="ip")
def get_ip(request: Request) -> dict:
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return {"code": 200, "msg": "success", "data": {"ip": ip}}

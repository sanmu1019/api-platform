from fastapi import APIRouter, Depends

from core.depends import verify_api_key

router = APIRouter(prefix="/api", tags=["demo"], dependencies=[Depends(verify_api_key)])


@router.get("/demo", name="demo")
def demo() -> dict:
    return {"code": 200, "msg": "success", "data": "这是一个测试接口"}

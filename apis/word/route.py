import random

from fastapi import APIRouter, Depends

from apis.data_loader import load_lines
from core.depends import verify_api_key

router = APIRouter(prefix="/api/word", tags=["word"], dependencies=[Depends(verify_api_key)])


@router.get("/random", name="word")
def random_word() -> dict:
    return {"code": 200, "msg": "success", "data": {"word": random.choice(load_lines("words.txt"))}}

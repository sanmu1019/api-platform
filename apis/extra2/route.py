from __future__ import annotations

import json
import logging
import random

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from core.depends import verify_api_key
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools2", tags=["tools2"], dependencies=[Depends(verify_api_key)])


# 车牌归属地静态数据
CAR_PLATE = {
    "京": "北京", "津": "天津", "沪": "上海", "渝": "重庆",
    "冀": "河北", "豫": "河南", "云": "云南", "辽": "辽宁", "黑": "黑龙江",
    "湘": "湖南", "皖": "安徽", "鲁": "山东", "新": "新疆", "苏": "江苏",
    "浙": "浙江", "赣": "江西", "鄂": "湖北", "桂": "广西", "甘": "甘肃",
    "晋": "山西", "蒙": "内蒙古", "陕": "陕西", "吉": "吉林", "闽": "福建",
    "贵": "贵州", "粤": "广东", "川": "四川", "青": "青海", "藏": "西藏",
    "琼": "海南", "宁": "宁夏",
}


@router.get("/carplate", name="carplate_query")
def carplate_query(code: str = Query(..., description="车牌第一个字，如 京A")):
    """根据车牌查询归属地。"""
    if not code:
        raise HTTPException(status_code=400, detail="请输入车牌")
    first_char = code[0].upper()
    if first_char in CAR_PLATE:
        return {"code": 200, "msg": "success", "data": {"code": code, "province": CAR_PLATE[first_char]}}
    raise HTTPException(status_code=404, detail="未知车牌")


# 答案之书预设答案
ANSWERS = [
    "是的，毫无疑问。",
    "绝对不行。",
    "现在还不是时候。",
    "事在人为。",
    "听从你内心的声音。",
    "可以试试。",
    "别抱太大希望。",
    "会有意外收获。",
    "放弃吧。",
    "坚持下去就会成功。",
    "需要更多的信息。",
    "顺其自然。",
    "现在做正好。",
    "不要急，再等等。",
    "你已经知道答案了。",
    "结果会超出你的预期。",
    "小心谨慎为好。",
    "大胆去做吧。",
    "有人会帮助你。",
    "这是个错误的决定。",
]


@router.get("/answer", name="answer_book")
def answer_book(question: str = Query(..., description="你想问的问题")):
    """答案之书，随机给出一个答案。"""
    answer = random.choice(ANSWERS)
    return {"code": 200, "msg": "success", "data": {"question": question, "answer": answer}}


# 今天吃什么预设美食
FOODS = [
    "火锅", "烧烤", "麻辣烫", "牛肉面", "炒饭", "饺子", "包子", "面条",
    "汉堡", "披萨", "寿司", "烤肉", "小龙虾", "炸鸡", "薯条", "可乐",
    "麻辣烫", "麻辣香锅", "冒菜", "黄焖鸡米饭", "沙县小吃", "兰州拉面",
    "黄焖鸡", "酸菜鱼", "水煮鱼", "回锅肉", "宫保鸡丁", "鱼香肉丝",
    "西红柿鸡蛋面", "蛋炒饭", "炒粉", "粥", "煎饼果子", "手抓饼",
]


@router.get("/food", name="food_recommend")
def food_recommend():
    """今天吃什么，随机推荐美食。"""
    return {"code": 200, "msg": "success", "data": {"food": random.choice(FOODS)}}


# 人品评分
@router.get("/luck", name="luck_score")
def luck_score(name: str = Query(..., description="你的名字")):
    """今日人品评分。"""
    random.seed(name + str(__import__("datetime").date.today()))
    score = random.randint(0, 100)
    tags = ["大吉", "中吉", "小吉", "平", "小凶", "中凶", "大凶"]
    tag = random.choice(tags)
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "name": name,
            "score": score,
            "tag": tag,
            "date": str(__import__("datetime").date.today()),
        },
    }


@router.get("/earthquake", name="earthquake_list")
async def earthquake_list(limit: int = Query(10, ge=1, le=50, description="返回数量，1-50")):
    """获取最近地震信息。"""
    try:
        async with httpx.AsyncClient(
            timeout=10,
            verify=not (settings.debug and not settings.is_production),
        ) as client:
            resp = await client.get("https://api.wolfx.jp/jma_earthquake.json")
            data = resp.json()
            # 截断返回数量
            if isinstance(data, list):
                data = data[:limit]
            elif isinstance(data, dict):
                # 如果是字典，尝试截断列表字段
                for key, value in data.items():
                    if isinstance(value, list):
                        data[key] = value[:limit]
            return {"code": 200, "msg": "success", "data": data}
    except HTTPException:
        raise
    except Exception:
        logger.exception("地震查询失败")
        raise HTTPException(status_code=502, detail="上游地震数据请求失败")

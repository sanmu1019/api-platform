import re

from fastapi import APIRouter, Depends, HTTPException

from apis.data_loader import load_json
from core.depends import verify_api_key

router = APIRouter(prefix="/api/phone", tags=["phone"], dependencies=[Depends(verify_api_key)])


@router.get("/{phone}", name="phone")
def phone_lookup(phone: str) -> dict:
    if not re.fullmatch(r"1[3-9]\d{9}", phone):
        raise HTTPException(status_code=400, detail="手机号格式不正确")

    prefix7 = phone[:7]
    prefix3 = phone[:3]
    isp = province = city = ""
    known = False

    # 优先用 tools/build_datasets.py --phone 生成的 51 万条 7 位号段表。
    # 它把 [运营商下标, 地区下标] 打包成一个整数，运营商和地区各自去重成表，
    # 不这么存的话文件要大好几倍。
    try:
        table = load_json("phone_prefix.json")
        packed = table["prefixes"].get(prefix7)
        if packed is not None:
            isp = table["isps"][packed // 1000]
            province, city = table["areas"][packed % 1000]
            known = True
    except (OSError, ValueError, KeyError, IndexError):
        table = None

    if not known:
        # 没生成过大表（或该号段不在表里）时，退回原来那份 3 位号段的小表，
        # 接口仍然可用，只是给不出城市
        legacy = load_json("phone_map.json")
        entry = legacy.get(prefix3)
        if entry:
            isp, province = entry
            known = True

    return {
        "code": 200,
        "msg": "success" if known else "unknown prefix",
        "data": {
            "phone": phone,
            "prefix": prefix3,
            "isp": isp or "未知运营商",
            "province": province or "未知地区",
            "city": city or "",
            "known": known,
            # 号段只能推出号码最初的归属，携号转网后未必是当前运营商
            "note": "号段仅供参考，携号转网后可能与实际运营商不符",
        },
    }

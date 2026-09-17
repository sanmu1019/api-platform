#!/usr/bin/env python3
"""从公开数据源构建 apis/data/ 下的语料文件。

起因：唐诗接口只有 3 首、成语 4 条、历史上的今天只收录 3 天，
"随机一首"实际每次都在极小的池子里挑，没有使用价值。

可重复执行：每次都从上游重新拉取并覆��输出。只写 apis/data/ 下的
几个文件，不改任何路由代码。

    pip install zhconv          # 仅构建期需要，服务运行时不依赖
    python tools/build_datasets.py --all
    python tools/build_datasets.py --poetry --tang-shards 8

数据来源：
    唐诗   chinese-poetry/chinese-poetry（繁体，本脚本转简体）
    一言   hitokoto-osc/sentences-bundle
    历史   PrintNow/TodayInHistory（维基百科清洗版）
    成语   本机 E:\\wxbot-ipad\\tmp\\chinese_xinhua_idiom.json，可用 --idiom-source 指定
"""

from __future__ import annotations

import argparse
import codecs
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parents[1] / "apis" / "data"
RAW = "https://raw.githubusercontent.com"
TANG_300 = f"{RAW}/chinese-poetry/chinese-poetry/master/{urllib.parse.quote('全唐诗')}/{urllib.parse.quote('唐诗三百首')}.json"
# 注意：路径里的中文经 quote 后含 %E5 这类序列，不能再用 % 格式化，否则会和 %d 冲突
TANG_SHARD = f"{RAW}/chinese-poetry/chinese-poetry/master/{urllib.parse.quote('全唐诗')}/poet.tang.{{}}.json"
HITOKOTO = f"{RAW}/hitokoto-osc/sentences-bundle/master/sentences/%s.json"
HISTORY = f"{RAW}/PrintNow/TodayInHistory/master/history_in_today.json"
DEFAULT_IDIOM_SOURCE = Path(r"E:\wxbot-ipad\tmp\chinese_xinhua_idiom.json")


def to_simplified(text: str) -> str:
    from zhconv import convert

    return convert(text, "zh-cn")


def fetch_json(url: str, *, retries: int = 3, timeout: int = 60):
    last = None
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "dataset-builder"})
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # 上游偶发 5xx / 连接重置，退避重试
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"拉取失败 {url}: {last}")


def write_json(name: str, payload) -> None:
    path = DATA_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    size = path.stat().st_size / 1024
    count = len(payload)
    print(f"  写入 {name:22} {count:>6} 条  {size:>8.0f} KB")


def write_lines(name: str, rows) -> None:
    path = DATA_DIR / name
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"  写入 {name:22} {len(rows):>6} 行  {path.stat().st_size/1024:>8.0f} KB")


# ---------------------------------------------------------------------------
# 唐诗
# ---------------------------------------------------------------------------

def build_poetry(shards: int) -> None:
    print(f"[唐诗] 唐诗三百首 + 全唐诗 {shards} 个分片")
    raw = list(fetch_json(TANG_300))
    # 分片文件名不是 0/1/2，而是按 1000 递增：poet.tang.0/1000/…/57000.json
    for index in range(shards):
        offset = index * 1000
        raw.extend(fetch_json(TANG_SHARD.format(offset)))
        print(f"  已拉取 poet.tang.{offset}.json，累计 {len(raw)}")

    seen: set[str] = set()
    rows = []
    for item in raw:
        title = to_simplified(str(item.get("title") or "").strip())
        author = to_simplified(str(item.get("author") or "").strip())
        content = to_simplified("".join(item.get("paragraphs") or []).strip())
        # 源数据里有空标题/空正文，以及大量重复收录
        if not title or not content:
            continue
        key = f"{title}|{author}|{content}"
        if key in seen:
            continue
        seen.add(key)
        rows.append({"title": title, "author": author, "content": content})
    write_json("poetry_tang.json", rows)


# ---------------------------------------------------------------------------
# 一言
# ---------------------------------------------------------------------------

def build_yiyan() -> None:
    """一言 + 短句两份，同一份上游语料按长度切分。"""
    print("[一言 / 短句] hitokoto 全部分类")
    rows: list[str] = []
    seen: set[str] = set()
    for category in "abcdefghijkl":
        try:
            items = fetch_json(HITOKOTO % category)
        except RuntimeError as exc:
            print(f"  分类 {category} 跳过：{exc}")
            continue
        for item in items:
            text = str(item.get("hitokoto") or "").strip()
            # 换行会破坏按行存储的格式；过长的句子不适合"一言"场景
            if not text or "\n" in text or len(text) > 60:
                continue
            if text in seen:
                continue
            seen.add(text)
            rows.append(text)
        print(f"  分类 {category} 累计 {len(rows)}")
    rows.sort()
    write_lines("yiyan.txt", rows)

    # word/random 是"短句"场景，句子太长在群里刷屏，单独取一份 20 字以内的
    short = sorted(r for r in rows if len(r) <= 20)
    write_lines("words.txt", short)


# ---------------------------------------------------------------------------
# 历史上的今天
# ---------------------------------------------------------------------------

DELIM = "${{delimiter}}"
# 内容过滤词表。**被 .gitignore 忽略** —— 词表本身就是敏感词清单，不该随
# 公开仓库分发。本地由 tmp_probe/filter_history_sensitive.py --emit-blocklist 生成。
# 缺这个文件时不会静默放行：下面会打印醒目告警，提示语料未经过滤。
BLOCKLIST_FILE = DATA_DIR / "history_today.blocklist.txt"


def _load_blocklist() -> tuple[list[str], list[tuple[str, ...]]]:
    """读词表。`word` 为子串规则，`+w1+w2` 为「同时出现」规则。"""
    subs: list[str] = []
    combos: list[tuple[str, ...]] = []
    for raw in BLOCKLIST_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("+"):
            parts = tuple(p for p in line.split("+") if p)
            if parts:
                combos.append(parts)
        else:
            subs.append(line)
    return subs, combos


def sanitize_history(data: dict[str, list[str]]) -> tuple[dict[str, list[str]], int]:
    """剔除不宜在境内公开展示的条目，返回 (过滤后数据, 剔除条数)。

    在**子事件**粒度过滤：语料里有条目用 `${{delimiter}}` 把多条事件拼在一起
    （多为「生于今日」名单），按整条剔除会连带删掉同组的无辜邻居。
    """
    if not BLOCKLIST_FILE.exists():
        print(f"  ⚠ 未找到 {BLOCKLIST_FILE.name}，语料【未做内容过滤】。")
        print("    若准备公开部署，请先运行：")
        print("      python tmp_probe/filter_history_sensitive.py "
              "--emit-blocklist --roc all --movements drop")
        return data, 0

    subs, combos = _load_blocklist()

    def blocked(text: str) -> bool:
        return any(w in text for w in subs) or any(all(w in text for w in c) for c in combos)

    out: dict[str, list[str]] = {}
    dropped = 0
    for day, events in data.items():
        kept: list[str] = []
        for entry in events:
            parts = entry.split(DELIM)
            alive = [s for s in parts if not blocked(s)]
            dropped += len(parts) - len(alive)
            if alive:
                kept.append(DELIM.join(alive))
        # 日期键即使被清空也保留，否则 /api/history/today 的 covered_dates 会变
        out[day] = kept
    return out, dropped


def build_history() -> None:
    print("[历史上的今天] 拉取维基百科清洗版（约 6 MB）")
    raw = fetch_json(HISTORY)
    grouped: dict[str, list[str]] = {}
    for item in raw:
        try:
            month = int(item.get("month"))
            day = int(item.get("day"))
        except (TypeError, ValueError):
            continue
        if not (1 <= month <= 12 and 1 <= day <= 31):
            continue
        text = str(item.get("data") or "").strip()
        if not text:
            continue
        try:
            year = int(item.get("year"))
        except (TypeError, ValueError):
            year = None
        if year is None:
            label = text
        elif year < 0:
            label = f"公元前{abs(year)}年：{text}"
        else:
            label = f"{year}年：{text}"
        grouped.setdefault(f"{month:02d}-{day:02d}", []).append(label)

    for key in grouped:
        # 同一天条目很多，按年份先后排序，读起来才像"这一天发生了什么"
        grouped[key].sort(key=lambda s: _year_key(s))
    ordered = {key: grouped[key] for key in sorted(grouped)}
    print(f"  覆盖 {len(ordered)} 天，平均每天 {sum(len(v) for v in ordered.values())/max(1,len(ordered)):.0f} 条")
    ordered, dropped = sanitize_history(ordered)
    print(f"  内容过滤：剔除 {dropped} 条子事件")
    write_json("history_today.json", ordered)


def _year_key(label: str) -> int:
    match = re.match(r"^公元前(\d+)年：", label)
    if match:
        return -int(match.group(1))
    match = re.match(r"^(\d+)年：", label)
    return int(match.group(1)) if match else 0


# ---------------------------------------------------------------------------
# 成语
# ---------------------------------------------------------------------------

def build_idioms(source: Path) -> None:
    print(f"[成语] 读取本地词典 {source}")
    if not source.exists():
        print(f"  跳过：找不到 {source}，可用 --idiom-source 指定")
        return
    raw = json.loads(source.read_text(encoding="utf-8"))
    rows = []
    seen: set[str] = set()
    for item in raw:
        word = str(item.get("word") or "").strip()
        if not word or word in seen:
            continue
        seen.add(word)
        rows.append({
            "word": word,
            # 路由里按 pinyin 做小写包含匹配，去掉声调更容易命中
            "pinyin": str(item.get("pinyin") or "").strip(),
            "explain": str(item.get("explanation") or "").strip(),
        })
    write_json("idioms.json", rows)





# ---------------------------------------------------------------------------
# 手机号归属地
# ---------------------------------------------------------------------------

PHONE_SQL = f"{RAW}/dannyhu926/phone_location/master/mysql/phone_location.sql"
PHONE_ROW = re.compile(
    r"\(\d+,\s*'(\d{3})',\s*'(\d{7})',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'"
)


def build_phone() -> None:
    """7 位号段 -> 省/市/运营商。

    上游是 77 MB 的 SQL dump（51 万行），直接入库不现实，所以流式下载、
    边读边用正则抽字段，只把需要的三列留下，原文件不落盘。

    落盘用字典压缩：运营商和"省+市"各自去重成表，号段只存两个下标。
    直接存字符串的话文件会大好几倍。
    """
    print("[手机号归属地] 流式解析 77 MB SQL（原文件不落盘）")
    isps: list[str] = []
    isp_index: dict[str, int] = {}
    areas: list[list[str]] = []
    area_index: dict[tuple[str, str], int] = {}
    prefixes: dict[str, list[int]] = {}

    response = requests.get(PHONE_SQL, timeout=180, stream=True)
    response.raise_for_status()
    # 必须用增量解码器：一个中文字符是 3 字节，正好跨在两个分块边界上时，
    # 对每个分块单独 decode 会把它拆成两半变成乱码（"中国移动"曾被解出
    # "中国��动"）。增量解码器会把不完整的字节留到下一块。
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    pending = ""
    read = 0
    next_report = 16 << 20
    for chunk in response.iter_content(1 << 20):
        read += len(chunk)
        pending += decoder.decode(chunk)
        # 按行切；最后一段可能被截断，留到下一轮再拼
        lines = pending.split("\n")
        pending = lines.pop()
        for line in lines:
            for _pref3, pref7, province, city, isp in PHONE_ROW.findall(line):
                if isp not in isp_index:
                    isp_index[isp] = len(isps)
                    isps.append(isp)
                key = (province, city)
                if key not in area_index:
                    area_index[key] = len(areas)
                    areas.append([province, city])
                # 打包成一个整数：运营商 23 种、地区 360 个，乘 1000 不会撞
                prefixes[pref7] = isp_index[isp] * 1000 + area_index[key]
        if read >= next_report:
            print(f"  已读 {read/1024/1024:.0f} MB，号段 {len(prefixes)}")
            next_report += 16 << 20
    pending += decoder.decode(b"", final=True)
    for line in pending.splitlines():
        for _pref3, pref7, province, city, isp in PHONE_ROW.findall(line):
            if isp not in isp_index:
                isp_index[isp] = len(isps)
                isps.append(isp)
            key = (province, city)
            if key not in area_index:
                area_index[key] = len(areas)
                areas.append([province, city])
            prefixes[pref7] = isp_index[isp] * 1000 + area_index[key]

    assert len(areas) < 1000, f"地区数 {len(areas)} 超过打包上限"
    payload = {"isps": isps, "areas": areas, "prefixes": prefixes}
    print(f"  运营商 {len(isps)} 种，地区 {len(areas)} 个，号段 {len(prefixes)} 条")
    # 这份 51 万条，缩进会让体积翻一倍多，单独用紧凑写法
    path = DATA_DIR / "phone_prefix.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  写入 phone_prefix.json    {len(prefixes):>6} 条  {path.stat().st_size/1024:>8.0f} KB")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--poetry", action="store_true")
    parser.add_argument("--yiyan", action="store_true")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--idioms", action="store_true")
    parser.add_argument("--phone", action="store_true")
    parser.add_argument("--tang-shards", type=int, default=5, help="全唐诗分片数，每片 1000 首，上游共 58 片")
    parser.add_argument("--idiom-source", type=Path, default=DEFAULT_IDIOM_SOURCE)
    args = parser.parse_args()

    if not any([args.all, args.poetry, args.yiyan, args.history, args.idioms, args.phone]):
        parser.error("至少指定一项，或用 --all")

    if args.all or args.poetry:
        build_poetry(args.tang_shards)
    if args.all or args.yiyan:
        build_yiyan()
    if args.all or args.history:
        build_history()
    if args.all or args.idioms:
        build_idioms(args.idiom_source)
    if args.all or args.phone:
        build_phone()
    print("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

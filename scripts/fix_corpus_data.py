"""语料数据订正（唐诗错字 / 成语拼音 IPA / 符号错位还原 / 成语释义缺失的左双引号）。

用法：

    python scripts/fix_corpus_data.py            # 只报告，不写文件
    python scripts/fix_corpus_data.py --apply    # 实际写入

四项订正，按顺序执行（顺序有意义：符号还原必须先做，它还原出来的「，」
是第 4 步切分引号时的合法切分点）：

1. 唐诗《在岳咏蝉》→《在狱咏蝉》。骆宾王的名篇是《在狱咏蝉》，语料写错了。

2. 成语拼音里的 IPA 字符 `ɡ`(U+0261) 换成 ASCII `g`(U+0067)。数据源混用了两种
   字形，肉眼几乎一样，但会让按拼音检索/比对的结果对不上。

3. **符号错位还原**。整份语料里有 922 个字符在转码时被映射成了数学/杂项符号，
   全部出现在「本义 → 引申义」的衔接处。每个符号的还原值都由上下文实证确定
   （见 `SYMBOL_FIX` 的注释，命中率 100% 的那几个都标了分母）：

       ◇ ×814 → ，后      （◇昆→后昆、◇世视为→后世、◇辈→后辈）
       ∶ ×39  → ，         （困难∶事情在实现 → 困难，事情在实现）
       ≤ ×17  → ，
       ‖ ×13  → ，
       × ×10  → ，毫      （乱做×无顾忌 → 毫无顾忌）
       ⊥ ×10  → ，和      （苟同⊥睦地相处 → 和睦地相处）
       → ×5   → ，胡      （锺繇→昭 → 胡昭）
       ♂ ×5   → ，横      （暴戾♂行凶暴 → 横行凶暴）
       § ×5   → ，红      （绿叶§花衰败 → 红花衰败）
       ↑ ×4   → ，狐      （假借↑狸 → 狐狸）

   被还原的汉字全是拼音 h 开头的字（后/毫/和/胡/横/红/狐），符合 GBK 码位
   按拼音排序、区间错位后整段落到符号区的特征。∶ ≤ ‖ 三者的具体汉字无法从
   上下文唯一确定，只还原成逗号，不猜汉字。

4. 成语释义里**全部 4420 个右双引号 `”` 都没有配对的左双引号** —— 整份语料
   `“` 出现 0 次，是数据源系统性丢失，不是零星缺漏。这里按「就近引导词」把
   左引号补回去。

第 4 步是启发式，判据是：

- 从 `”` 往左扫，遇到 `“”‘’！？…（）【】《》` 就停（不跨越前一个引用）；
- 扫描过程中每个「引导词之后」和「句读之后」都是一个候选切分点；
- 候选打分：被引词本身是语料里的成语 +4、前一字是引导词 +2、被引词内无句读 +1；
- 取分最高者，同分取更长者。引导词表见 `LEAD_IN`。

**精度实测**（`tmp_probe/sample_precision.py`，按置信度分层随机抽样）：

- 被引词命中语料成语库 3640 处，抽样几乎全对；
- 未命中但长度 ≤2 的 361 处（`没同“殁”`、`县，通“悬”` 这类通假字），
  抽 60 条只发现 1 处可疑（`见通现”` 切成了「通现」）；
- 未命中且长度 ≥3 的 363 处（`亦作“山外有山”` 这类异体名），抽 60 条约 4~5 处错。

合计精度约 98%，补 4364/4420（98.73%）。

为什么不再往下补：残余 56 处（1.27%）是局部上下文给不出可靠信号的情况，
且语料本身在该处已损坏（`◇` 之外还有 `殂相似`、`眒字`、`棕福寿` 等零星错字）。
实测过「扩大引导词表 + 句首候选」的方案，覆盖率能到 99.8%，但边际新增的
47 处里约 24% 是错的（如 `耸膊成山` 会切成「了一个山」、`苦海无边` 会切成
「岸」），**错误率是 A 方案的 14 倍**。错引号会静默改变语义，缺引号只是显眼的
数据瑕疵，因此宁可留白。补不上的**保持原样**，不猜。

（回滚：`backup/20260914-1620-remaining-fixes/apis/data/` 是 A 方案前的原始副本；
`backup/20260914-1730-symbol-repair/apis/data/` 是仅补引号、未做符号还原的副本。）
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POETRY = ROOT / "apis" / "data" / "poetry_tang.json"
IDIOMS = ROOT / "apis" / "data" / "idioms.json"

# 唐诗标题错字
POETRY_TITLE_FIX = {"在岳咏蝉": "在狱咏蝉"}
# 拼音里混入的 IPA 字符 → ASCII
IPA_FIX = {"\u0261": "g"}

# 转码错位还原：符号 → 还原文本。值后面的注释是实证依据与命中率。
SYMBOL_FIX = {
    "\u25c7": "\uff0c\u540e",  # ◇ → ，后   814/814 后接字均与「后」成词
    "\u2236": "\uff0c",        # ∶ → ，     39 处均为释义衔接位
    "\u2264": "\uff0c",        # ≤ → ，     17 处同上
    "\u2016": "\uff0c",        # ‖ → ，     13 处同上
    "\u00d7": "\uff0c\u6beb",  # × → ，毫   10/10（毫无顾忌/毫无线索/毫无畏惧）
    "\u22a5": "\uff0c\u548c",  # ⊥ → ，和   10/10（和睦相处/和光混合/和尚面壁）
    "\u2192": "\uff0c\u80e1",  # → → ，胡   5/5（胡昭/胡地/胡须）
    "\u2642": "\uff0c\u6a2a",  # ♂ → ，横   5/5（横行凶暴/横着长矛/横眉怒目）
    "\u00a7": "\uff0c\u7ea2",  # § → ，红   5/5（红刀子/红花衰败/红润的脸）
    "\u2191": "\uff0c\u72d0",  # ↑ → ，狐   4/4（狐狸假借/狐性多疑/狐皮衣服）
}

LEFT_QUOTE = "\u201c"
RIGHT_QUOTE = "\u201d"
HARD_STOP = set("\u201c\u201d\u2018\u2019！？…（）()【】《》")
SENTENCE_END = set("。，；、：")
LEAD_IN = set("为通同作见指称叫即如曰谓述解引与犹异象音有")
MAX_TERM = 12


def _candidates(text: str, close_idx: int) -> list[dict]:
    """列出某个 `”` 左侧所有可能的切分点。"""
    out: list[dict] = []
    j = close_idx - 1
    while j >= 0 and text[j] not in HARD_STOP:
        term = text[j + 1:close_idx]
        if term and len(term) <= MAX_TERM:
            if text[j] in LEAD_IN or text[j] in SENTENCE_END:
                out.append({"pos": j + 1, "term": term, "lead": text[j] in LEAD_IN})
        j -= 1
    return out


def _score(candidate: dict, words: set[str]) -> int:
    score = 0
    if candidate["term"] in words:
        score += 4
    if candidate["lead"]:
        score += 2
    if not any(ch in SENTENCE_END for ch in candidate["term"]):
        score += 1
    return score


def insert_left_quotes(explain: str, words: set[str]) -> tuple[str, int, int]:
    """给 explain 里所有孤立的 `”` 补上左引号。返回 (新文本, 补了几处, 几处没补上)。"""
    closes = [m.start() for m in re.finditer(RIGHT_QUOTE, explain)]
    if not closes:
        return explain, 0, 0

    positions: list[int] = []
    missed = 0
    for close_idx in closes:
        # 已经配对了就跳过（本语料里不会出现，但保持幂等）
        if LEFT_QUOTE in explain[:close_idx]:
            continue
        candidates = _candidates(explain, close_idx)
        if not candidates:
            missed += 1
            continue
        best = max(candidates, key=lambda c: (_score(c, words), len(c["term"])))
        positions.append(best["pos"])

    if not positions:
        return explain, 0, missed

    result = explain
    for pos in sorted(set(positions), reverse=True):
        result = result[:pos] + LEFT_QUOTE + result[pos:]
    return result, len(set(positions)), missed


def repair_symbols(explain: str) -> tuple[str, int]:
    """还原转码错位产生的符号。返回 (新文本, 还原了几处)。"""
    hits = 0
    for bad, good in SYMBOL_FIX.items():
        n = explain.count(bad)
        if n:
            hits += n
            explain = explain.replace(bad, good)
    return explain, hits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="实际写回文件")
    args = parser.parse_args()

    # ---- 1. 唐诗标题 ----
    poetry = json.loads(POETRY.read_text(encoding="utf-8"))
    poetry_hits = []
    for item in poetry:
        fixed = POETRY_TITLE_FIX.get(item.get("title", ""))
        if fixed:
            poetry_hits.append((item["title"], fixed))
            item["title"] = fixed
    print(f"[1] 唐诗标题订正 {len(poetry_hits)} 处：{poetry_hits}")

    # ---- 2. 成语拼音 IPA ----
    idioms = json.loads(IDIOMS.read_text(encoding="utf-8"))
    ipa_hits = []
    for item in idioms:
        pinyin = item.get("pinyin", "")
        new_pinyin = pinyin
        for bad, good in IPA_FIX.items():
            new_pinyin = new_pinyin.replace(bad, good)
        if new_pinyin != pinyin:
            ipa_hits.append((item["word"], pinyin, new_pinyin))
            item["pinyin"] = new_pinyin
    print(f"[2] 成语拼音 IPA 订正 {len(ipa_hits)} 条：")
    for word, old, new in ipa_hits:
        print(f"      {word}: {old} -> {new}")

    # ---- 3. 符号错位还原 ----
    per_symbol = {bad: [0, 0] for bad in SYMBOL_FIX}  # [条目数, 处数]
    sym_entries = 0
    sym_total = 0
    sym_samples = []
    for item in idioms:
        explain = item.get("explain", "")
        if not any(bad in explain for bad in SYMBOL_FIX):
            continue
        new_explain, hits = repair_symbols(explain)
        if not hits:
            continue
        sym_entries += 1
        sym_total += hits
        for bad in SYMBOL_FIX:
            n = explain.count(bad)
            if n:
                per_symbol[bad][0] += 1
                per_symbol[bad][1] += n
        if len(sym_samples) < 4:
            sym_samples.append((item["word"], explain, new_explain))
        item["explain"] = new_explain
    print(f"[3] 符号错位还原：涉及 {sym_entries} 条、还原 {sym_total} 处")
    for bad, (entries, cnt) in per_symbol.items():
        if cnt:
            print(f"      {bad} ×{cnt:>4}  (分布在 {entries} 条)  ->  {SYMBOL_FIX[bad]!r}")
    for word, old, new in sym_samples:
        print(f"      {word}")
        print(f"        旧: {old[:76]}")
        print(f"        新: {new[:78]}")

    # ---- 4. 成语释义左引号 ----
    words = {item["word"] for item in idioms}
    fixed_entries = 0
    fixed_quotes = 0
    missed_quotes = 0
    samples = []
    for item in idioms:
        explain = item.get("explain", "")
        if RIGHT_QUOTE not in explain:
            continue
        new_explain, added, missed = insert_left_quotes(explain, words)
        missed_quotes += missed
        if added:
            fixed_entries += 1
            fixed_quotes += added
            if len(samples) < 5:
                samples.append((item["word"], explain, new_explain))
            item["explain"] = new_explain
    print(f"[4] 成语释义补左引号：涉及 {fixed_entries} 条、补 {fixed_quotes} 处；"
          f"{missed_quotes} 处找不到引导词，保持原样")
    for word, old, new in samples:
        print(f"      {word}")
        print(f"        旧: {old[:76]}")
        print(f"        新: {new[:78]}")

    if not args.apply:
        print("\n[dry-run] 未写入。加 --apply 生效。")
        return

    # 原文件用 indent=1（数组元素缩进 1 空格、键缩进 2 空格）、**不带尾换行**、
    # 行尾是 CRLF，照原样写回；否则整份 4.7MB 文件会被重排，diff 无法阅读。
    # 已用「读入→重建→比对」确认这样写回与原文件逐字节一致。
    # newline 必须显式指定：默认的 newline=None 会在 Windows 上写 CRLF、
    # 在 Linux 上写 LF，同一份语料在两种平台上产出不同文件。
    for path, payload in ((POETRY, poetry), (IDIOMS, idioms)):
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1),
            encoding="utf-8",
            newline="\r\n",
        )
    print(f"\n已写入 {POETRY.name} 与 {IDIOMS.name}")


if __name__ == "__main__":
    main()

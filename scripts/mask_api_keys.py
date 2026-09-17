"""一次性迁移：把历史日志/统计中的明文 Api-Key 脱敏。

背景
----
`access_logs.api_key` 与 `api_stats.api_key` 原先直接存明文 Key。
导出一份访问日志（后台支持 CSV 导出）或泄露一份数据库备份，就等于泄露凭据。
代码已改为写入脱敏值，但历史行仍是明文，需要用本脚本处理一遍。

脱敏规则见 `core.middleware.mask_api_key`：保留前 8 位 + sha256 前 12 位。
同一 Key 始终映射到同一结果，所以按 Key 分组统计不受影响。
`public`（未带 Key 的公开调用）与空值保持原样。

用法
----
    python scripts/mask_api_keys.py            # 预演，只统计不写入
    python scripts/mask_api_keys.py --apply    # 实际执行

建议先备份数据库：
    cp data/api_platform.sqlite3 data/api_platform.sqlite3.bak
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import get_conn  # noqa: E402
from core.middleware import mask_api_key  # noqa: E402

TABLES = ("api_stats", "access_logs")
# 这两个值不是真实 Key，不该被脱敏。
KEEP_VALUES = {"", "public"}
# 已脱敏的值形如 "ak_EXAMPLE1…a1b2c3d4e5f6"，含省略号；用它判断是否处理过。
MASKED_MARKER = "…"


def _needs_masking(value: str | None) -> bool:
    if not value or value in KEEP_VALUES:
        return False
    return MASKED_MARKER not in value


def main() -> int:
    apply = "--apply" in sys.argv
    total_changed = 0

    with get_conn() as conn:
        for table in TABLES:
            rows = conn.execute(
                f"SELECT DISTINCT api_key FROM {table} WHERE api_key IS NOT NULL AND api_key != ''"
            ).fetchall()
            targets = [row["api_key"] for row in rows if _needs_masking(row["api_key"])]

            affected = 0
            if targets:
                placeholders = ",".join("?" * len(targets))
                affected = conn.execute(
                    f"SELECT COUNT(*) AS c FROM {table} WHERE api_key IN ({placeholders})",
                    targets,
                ).fetchone()["c"]

            print(f"{table}: {len(targets)} 个明文 Key，涉及 {affected} 行")
            for key in targets:
                print(f"    {key}  ->  {mask_api_key(key)}")

            if apply and targets:
                for key in targets:
                    conn.execute(
                        f"UPDATE {table} SET api_key = ? WHERE api_key = ?",
                        (mask_api_key(key), key),
                    )
                total_changed += affected
                print(f"  -> 已写入 {affected} 行")

    if apply:
        print(f"\n完成，共改写 {total_changed} 行。")
    else:
        print("\n这是预演，未写入任何数据。确认无误后加 --apply 执行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""清理真实库里的测试污染行（TestClient 产生的假流量）。

## 背景

`tests/conftest.py` 通过环境变量 `API_PLATFORM_DATABASE_PATH` 把测试库指向临时目录，
但这套隔离是后加的 —— 在此之前跑测试会直接写进 `data/api_platform.sqlite3`，
于是真实库里堆了上万行假流量：`client_ip` 与 `user_agent` 都是 `testclient`。

后果：后台仪表盘的 `total` / `access_total` / `error_total` 里 70% 是测试数据，
统计完全失真。

## 识别依据（为什么可信）

`access_logs` 中 `client_ip='testclient'` 与 `user_agent='testclient'` 两个条件
**完全重合**（实测都是 9114 行，无交叉），说明这批行是同源的、由 TestClient 写入的，
不存在"误伤真实请求"的情况 —— 真实客户端的 IP 不可能是字符串 `testclient`。

`api_stats` 同理，按 `client_ip='testclient'` 识别（5300 行）。
注意 `api_stats` 里另有 3203 行 `client_ip='127.0.0.1'`，那是本地 curl/浏览器调试的
真实调用，**不属于污染，不删**。

## 用法

    python scripts/clean_test_pollution.py            # 只报告，不写库（默认）
    python scripts/clean_test_pollution.py --apply    # 实际删除并 VACUUM

`--apply` 前会自动把库备份到 `backup/<时间戳>-db-preclean/`。
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "api_platform.sqlite3"

TESTCLIENT = "testclient"


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    q = conn.execute
    return {
        "access_total": q("SELECT COUNT(*) FROM access_logs").fetchone()[0],
        "access_polluted": q(
            "SELECT COUNT(*) FROM access_logs WHERE client_ip = ? OR user_agent = ?",
            (TESTCLIENT, TESTCLIENT),
        ).fetchone()[0],
        "stats_total": q("SELECT COUNT(*) FROM api_stats").fetchone()[0],
        "stats_polluted": q(
            "SELECT COUNT(*) FROM api_stats WHERE client_ip = ?", (TESTCLIENT,)
        ).fetchone()[0],
        "stats_localhost": q(
            "SELECT COUNT(*) FROM api_stats WHERE client_ip = '127.0.0.1'"
        ).fetchone()[0],
    }


def report(before: dict[str, int]) -> None:
    print("access_logs  总行数 %6d，其中 testclient 污染 %6d（%.0f%%）"
          % (before["access_total"], before["access_polluted"],
             100.0 * before["access_polluted"] / max(1, before["access_total"])))
    print("api_stats    总行数 %6d，其中 testclient 污染 %6d（%.0f%%）"
          % (before["stats_total"], before["stats_polluted"],
             100.0 * before["stats_polluted"] / max(1, before["stats_total"])))
    print("api_stats    保留 127.0.0.1 本地调试 %6d 行（非污染）" % before["stats_localhost"])


def backup_db() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    dest_dir = ROOT / "backup" / f"{stamp}-db-preclean"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / DB.name
    shutil.copy2(DB, dest)
    print(f"已备份 -> {dest.relative_to(ROOT)}")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="清理真实库里的 TestClient 测试污染")
    ap.add_argument("--apply", action="store_true", help="实际删除（默认只报告）")
    ap.add_argument(
        "--no-backup",
        action="store_true",
        help="跳过自动备份（仅用于清理少量复写行；大清理不要用）",
    )
    args = ap.parse_args()

    if not DB.exists():
        print(f"数据库不存在：{DB}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB)
    try:
        before = counts(conn)
        print("=== 清理前 ===")
        report(before)

        if not args.apply:
            print("\n[dry-run] 未写库。加 --apply 实际执行。")
            return 0

        if not before["access_polluted"] and not before["stats_polluted"]:
            print("\n没有需要清理的行。")
            return 0

        if args.no_backup:
            print("\n[--no-backup] 跳过备份")
        else:
            backup_db()

        cur1 = conn.execute(
            "DELETE FROM access_logs WHERE client_ip = ? OR user_agent = ?",
            (TESTCLIENT, TESTCLIENT),
        )
        cur2 = conn.execute(
            "DELETE FROM api_stats WHERE client_ip = ?", (TESTCLIENT,)
        )
        conn.commit()
        print(f"\n已删除 access_logs {cur1.rowcount} 行、api_stats {cur2.rowcount} 行")

        print("VACUUM 回收空间 ...")
        conn.execute("VACUUM")

        after = counts(conn)
        print("\n=== 清理后 ===")
        report(after)

        ok = (
            after["access_polluted"] == 0
            and after["stats_polluted"] == 0
            and after["access_total"] == before["access_total"] - before["access_polluted"]
            and after["stats_total"] == before["stats_total"] - before["stats_polluted"]
            and after["stats_localhost"] == before["stats_localhost"]
        )
        print("\n" + ("PASS: 污染清零，且未误伤 127.0.0.1 调试行" if ok else "FAIL: 结果与预期不符，请用备份回滚"))
        return 0 if ok else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

"""测试会话级配置：把数据库隔离到临时目录。

**为什么必须放在这里**：`core.config.settings` 是在模块 import 时由
`get_settings()` 求值、并被 `lru_cache` 缓存的。pytest 会先导入 conftest.py、
再导入测试模块，所以只有在这里（模块顶层）设置环境变量，才能赶在
`core.config` 被导入之前生效。

不这么做的话，`init_db()` 和各个用例会直接写进真实的
`data/api_platform.sqlite3`：注册用户、创建 Key、插入调用统计，
把本地/线上的数据搞脏。
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

# 独立于真实库的临时数据库；会话结束后整目录删除。
_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="api-platform-tests-"))
os.environ["API_PLATFORM_DATABASE_PATH"] = str(_TEST_DB_DIR / "test.sqlite3")


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    """测试会话结束后清理临时数据库目录。"""
    shutil.rmtree(_TEST_DB_DIR, ignore_errors=True)

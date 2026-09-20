from functools import lru_cache
import json
import logging
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


logger = logging.getLogger(__name__)

# 环境变量覆盖项的前缀，详见 get_settings()。
ENV_PREFIX = "API_PLATFORM_"

# 只有这些监听地址才算"没对外暴露"。
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_WEAK_ADMIN_TOKENS = {"", "admin888", "please-change-admin-token"}
_WEAK_API_KEYS = {"test123", "please-change-api-key"}


CONFIG_PATH = Path("config.json")


class Settings(BaseModel):
    app_name: str = "绿夜API"
    environment: str = "development"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    database_path: str = "./data/api_platform.sqlite3"

    # 生产环境必须通过 config.json 覆盖默认值。
    admin_token: str = "admin888"
    default_api_keys: str = "test123:测试用户"

    # 逗号分隔；为空表示不启用 CORS 中间件。
    cors_origins: str = ""

    enable_douyin: bool = True
    douyin_proxy: str = ""
    wxsph_cookie: str = ""
    require_api_key: bool = False
    rate_limit_per_minute: int = 120
    self_register_quota_per_day: int = 1000

    # 公网安全配置。
    public_security_enabled: bool = True
    allow_self_register: bool = True
    admin_ip_allowlist: str = ""
    admin_login_fail_limit: int = 5
    admin_login_fail_window_seconds: int = 300
    admin_public_path: str = "/manage-api"

    model_config = ConfigDict(extra="ignore")

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return (value or "development").strip().lower()

    @property
    def is_production(self) -> bool:
        return self.environment in {"prod", "production"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def admin_ip_allowlist_values(self) -> list[str]:
        return [item.strip() for item in self.admin_ip_allowlist.split(",") if item.strip()]

    @property
    def normalized_admin_path(self) -> str:
        value = (self.admin_public_path or "/manage-api").strip()
        if not value.startswith("/"):
            value = "/" + value
        return value.rstrip("/") or "/manage-api"

    @property
    def listens_publicly(self) -> bool:
        """监听地址是否不止本机。"""
        return (self.host or "").strip().lower() not in _LOOPBACK_HOSTS

    def _weak_credential_problems(self) -> list[str]:
        problems: list[str] = []
        if self.admin_token in _WEAK_ADMIN_TOKENS:
            problems.append("ADMIN_TOKEN 仍是默认值")
        for pair in self.default_api_keys.split(","):
            key = pair.partition(":")[0].strip()
            if key in _WEAK_API_KEYS:
                problems.append(f"DEFAULT_API_KEYS 中的 {key!r} 仍是默认值")
        return problems

    def validate_public_security(self) -> None:
        """校验对外暴露时的凭据强度。

        要点：不能只看 `environment`。只要 host 不是回环地址，服务就已经可以被
        外部访问了。原实现只判断 is_production，于是"监听 0.0.0.0、但 environment
        忘了改成 production"时，弱口令校验会被整体跳过 —— 后台口令就直接是默认值。

        因此这里以"是否对外监听"为准：生产环境直接拒绝启动；非生产环境打醒目告警，
        避免打断本地开发。
        """
        problems = self._weak_credential_problems()
        if not problems:
            return
        if self.is_production:
            raise RuntimeError(
                "生产环境禁止使用默认凭据，请在 config.json 中设置强随机值："
                + "；".join(problems)
            )
        if self.listens_publicly:
            logger.warning(
                "安全告警：服务监听 %s（可被外部访问），但仍在使用默认凭据 —— %s。"
                "如果这是线上环境，请立即在 config.json 中改为强随机值，"
                "并把 environment 设为 production。",
                self.host,
                "；".join(problems),
            )


@lru_cache
def get_settings() -> Settings:
    """读取配置：config.json 为基础，环境变量可覆盖。

    环境变量格式为 `API_PLATFORM_<字段名大写>`，例如：

        API_PLATFORM_DATABASE_PATH=./data/test.sqlite3

    加这层是为了让测试能指向独立的数据库，而不是写进真实库
    （见 tests/conftest.py）。也方便在容器 / CI 里临时覆盖单个配置项，
    不必改文件。
    """
    raw: dict = {}
    if CONFIG_PATH.exists():
        try:
            parsed = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"配置文件 {CONFIG_PATH} 不是合法 JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError(f"配置文件 {CONFIG_PATH} 顶层必须是 JSON 对象")
        raw = dict(parsed)

    raw.update(_env_overrides())
    return Settings(**raw)


def _env_overrides() -> dict[str, str]:
    """收集 `API_PLATFORM_*` 形式的环境变量覆盖项。"""
    overrides: dict[str, str] = {}
    for name in Settings.model_fields:
        value = os.environ.get(f"{ENV_PREFIX}{name.upper()}")
        if value is not None:
            overrides[name] = value
    return overrides


settings = get_settings()

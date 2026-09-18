from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from core.config import settings

logger = logging.getLogger(__name__)


API_CATALOG = [
    {
        "name": "demo",
        "path": "/api/demo",
        "title": "测试接口",
        "description": "返回一段测试内容。",
        "category": "基础服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 10,
    },
    {
        "name": "ip",
        "path": "/api/ip",
        "title": "IP 查询",
        "description": "返回客户端 IP 地址。",
        "category": "网络工具",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 20,
    },
    {
        "name": "time",
        "path": "/api/time",
        "title": "时间接口",
        "description": "返回当前时间戳和格式化时间。",
        "category": "基础服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 30,
    },
    {
        "name": "phone",
        "path": "/api/phone/{phone}",
        "title": "手机号归属地",
        "description": "根据号段返回模拟归属地。",
        "category": "生活服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 40,
    },
    {
        "name": "word",
        "path": "/api/word/random",
        "title": "随机短句",
        "description": "返回随机中文短句。",
        "category": "内容服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 50,
    },
    {
        "name": "yiyan",
        "path": "/api/yiyan",
        "title": "随机一言",
        "description": "返回一句随机中文短句，可用于文案、签名和页面点缀。",
        "category": "文案服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 60,
    },
    {
        "name": "avatar_random",
        "path": "/api/avatar/random",
        "title": "随机头像",
        "description": "根据 seed 生成随机头像 URL，适合测试用户头像和占位头像。",
        "category": "图片服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 70,
    },
    {
        "name": "short_hash",
        "path": "/api/short/hash",
        "title": "短码生成",
        "description": "根据 URL 在本地生成稳定短码，适合做短链接标识或缓存 Key。",
        "category": "工具服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 80,
    },
    {
        "name": "bilibili_cover",
        "path": "/api/bilibili/cover",
        "title": "B站封面信息",
        "description": "根据 BV 号返回 B 站公开视频信息接口地址，后续可扩展为服务端封面解析。",
        "category": "媒体服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 90,
    },
    {
        "name": "bing_daily",
        "path": "/api/bing/daily",
        "title": "必应每日图",
        "description": "获取必应每日图片信息，网络失败时返回兜底图片。",
        "category": "图片服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 100,
    },
    {
        "name": "tool_timestamp",
        "path": "/api/tool/timestamp",
        "title": "时间戳转换",
        "description": "将时间戳转换为格式化时间；不传参数时返回当前时间。",
        "category": "工具服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 110,
    },
    {
        "name": "tool_hash",
        "path": "/api/tool/hash",
        "title": "哈希计算",
        "description": "支持 md5、sha1、sha256、sha512 文本哈希计算。",
        "category": "工具服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 120,
    },
    {
        "name": "tool_base64",
        "path": "/api/tool/base64",
        "title": "Base64 编解码",
        "description": "支持 Base64 encode/decode。",
        "category": "工具服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 130,
    },
    {
        "name": "tool_uuid",
        "path": "/api/tool/uuid",
        "title": "UUID 生成",
        "description": "批量生成 UUID v4。",
        "category": "工具服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 140,
    },
    {
        "name": "tool_password",
        "path": "/api/tool/password",
        "title": "随机密码",
        "description": "生成指定长度的随机密码。",
        "category": "工具服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 150,
    },
    {
        "name": "tool_color",
        "path": "/api/tool/color",
        "title": "随机颜色",
        "description": "生成随机 HEX 和 RGB 颜色。",
        "category": "工具服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 160,
    },
    {
        "name": "tool_nickname",
        "path": "/api/tool/nickname",
        "title": "随机昵称",
        "description": "生成随机中文昵称。",
        "category": "文案服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 170,
    },
    {
        "name": "image_placeholder",
        "path": "/api/image/placeholder",
        "title": "占位图 URL",
        "description": "生成指定尺寸的占位图 URL。",
        "category": "图片服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 180,
    },
    {
        "name": "image_qrcode",
        "path": "/api/image/qrcode",
        "title": "二维码图片 URL",
        "description": "根据文本生成二维码图片 URL。",
        "category": "图片服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 190,
    },
    {
        "name": "api_version",
        "path": "/api/version",
        "title": "API 版本信息",
        "description": "返回当前 API 版本、兼容路径和推荐版本化路径。",
        "category": "系统服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 200,
    },
    {
        "name": "history_today",
        "path": "/api/history/today",
        "title": "历史上的今天",
        "description": "按 MM-DD 返回历史事件示例数据。",
        "category": "内容服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 280,
    },
    {
        "name": "idiom_search",
        "path": "/api/idiom/search",
        "title": "成语查询",
        "description": "按关键词查询成语释义和拼音。",
        "category": "教育服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 290,
    },
    {
        "name": "poetry_tang",
        "path": "/api/poetry/tang",
        "title": "唐诗接口",
        "description": "返回唐诗示例数据，支持关键词筛选。",
        "category": "教育服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 200,
    },
    {
        "name": "hot_platforms",
        "path": "/api/hot/platforms",
        "title": "热榜平台列表",
        "description": "返回支持的热榜平台列表（微博/百度/GitHub/B站）。",
        "category": "热榜聚合",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 210,
    },
    {
        "name": "hot_list",
        "path": "/api/hot/{platform}",
        "title": "平台热榜",
        "description": "获取指定平台的实时热榜，支持微博/百度/GitHub/B站，缓存5分钟。",
        "category": "热榜聚合",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 220,
    },
    {
        "name": "exchange_currencies",
        "path": "/api/exchange/currencies",
        "title": "货币列表",
        "description": "返回支持的汇率货币代码和名称（30+货币）。",
        "category": "金融服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 230,
    },
    {
        "name": "exchange_rate",
        "path": "/api/exchange/rate",
        "title": "汇率查询",
        "description": "查询两种货币之间的汇率，支持历史日期，数据来源欧洲央行。",
        "category": "金融服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 240,
    },
    {
        "name": "exchange_convert",
        "path": "/api/exchange/convert",
        "title": "货币转换",
        "description": "按实时汇率将一种货币金额转换为另一种货币。",
        "category": "金融服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 250,
    },
    {
        "name": "weather_geo",
        "path": "/api/weather/geo",
        "title": "城市搜索",
        "description": "按名称搜索城市，返回经纬度用于天气查询。",
        "category": "生活服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 260,
    },
    {
        "name": "weather_current",
        "path": "/api/weather/current",
        "title": "实时天气",
        "description": "按经纬度查询实时天气：温度、湿度、风力、天气现象。",
        "category": "生活服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 270,
    },
    {
        "name": "weather_forecast",
        "path": "/api/weather/forecast",
        "title": "多日天气预报",
        "description": "按经纬度查询1-16天天气预报，含最高/最低温、降水、日出日落。",
        "category": "生活服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 280,
    },
    {
        "name": "holiday_check",
        "path": "/api/holiday/check",
        "title": "节假日查询",
        "description": "查询指定日期是否为工作日、节假日或调休日。",
        "category": "生活服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 290,
    },
    {
        "name": "holiday_range",
        "path": "/api/holiday/range",
        "title": "节假日范围查询",
        "description": "查询日期范围内的所有节假日和调休上班日。",
        "category": "生活服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 300,
    },
    {
        "name": "lunar_day",
        "path": "/api/lunar/day",
        "title": "万年历老黄历",
        "description": "公历转农历，含干支、生肖、节气、宜忌、吉神方位、二十八星宿等。",
        "category": "生活服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 310,
    },
    {
        "name": "price_gold",
        "path": "/api/price/gold",
        "title": "黄金行情",
        "description": "纽约黄金期货实时行情：最新价、涨跌幅、最高最低、昨收。",
        "category": "金融服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 320,
    },
    {
        "name": "price_silver",
        "path": "/api/price/silver",
        "title": "白银行情",
        "description": "纽约白银期货实时行情。",
        "category": "金融服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 330,
    },
    {
        "name": "price_oil",
        "path": "/api/price/oil",
        "title": "原油行情",
        "description": "WTI纽约原油期货实时行情。",
        "category": "金融服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 340,
    },
    {
        "name": "price_all",
        "path": "/api/price/all",
        "title": "全部行情",
        "description": "一次性返回黄金、白银、原油全部行情。",
        "category": "金融服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 350,
    },
    {
        "name": "joke_random",
        "path": "/api/joke/random",
        "title": "随机段子",
        "description": "随机获取一条中文段子。",
        "category": "内容服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 360,
    },
    {
        "name": "joke_list",
        "path": "/api/joke/list",
        "title": "段子列表",
        "description": "分页获取段子列表。",
        "category": "内容服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 370,
    },
    {
        "name": "joke_detail",
        "path": "/api/joke/{id}",
        "title": "段子详情",
        "description": "按ID获取单条段子。",
        "category": "内容服务",
        "method": "GET",
        "response_type": "builtin",
        "response_body": "",
        "is_builtin": 1,
        "sort_order": 380,
    },
    ]

DEFAULT_SITE_SETTINGS = {
    "site_name": "绿夜API",
    "logo_text": "绿",
    "hero_title": "绿夜API · 免费公益接口平台",
    "hero_subtitle": "提供短视频去水印解析、开发者工具、内容聚合、图片服务等接口。",
}

API_PRESENTATION = {
    item["name"]: (item["title"], item["description"], item["category"])
    for item in API_CATALOG
}
API_PRESENTATION["douyin_parse"] = (
    "抖音无水印解析",
    "抖音去水印解析，支持图文、短视频和实况解析，支持分享短链接。",
    "短视频解析",
)

def _db_path() -> Path:
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path(), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_column(conn: sqlite3.Connection, table: str, name: str, ddl: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if name not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS apis (
                name TEXT PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name TEXT NOT NULL,
                api_key TEXT NOT NULL,
                path TEXT NOT NULL,
                client_ip TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL,
                client_ip TEXT,
                user_agent TEXT,
                api_key TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS site_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_api_stats_api_name ON api_stats(api_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_api_stats_created_at ON api_stats(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_created_at ON access_logs(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_access_logs_status_code ON access_logs(status_code)")

        _ensure_column(conn, "apis", "category", "category TEXT NOT NULL DEFAULT '默认分类'")
        _ensure_column(conn, "apis", "method", "method TEXT NOT NULL DEFAULT 'GET'")
        _ensure_column(conn, "apis", "response_type", "response_type TEXT NOT NULL DEFAULT 'json'")
        _ensure_column(conn, "apis", "response_body", "response_body TEXT NOT NULL DEFAULT '{}'")
        _ensure_column(conn, "apis", "status_code", "status_code INTEGER NOT NULL DEFAULT 200")
        _ensure_column(conn, "apis", "is_builtin", "is_builtin INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "apis", "sort_order", "sort_order INTEGER NOT NULL DEFAULT 100")
        _ensure_column(conn, "apis", "created_at", "created_at TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "apis", "updated_at", "updated_at TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "api_keys", "quota_per_day", "quota_per_day INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "api_keys", "used_today", "used_today INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "api_keys", "last_used_date", "last_used_date TEXT NOT NULL DEFAULT ''")
        _ensure_column(conn, "api_keys", "created_at", "created_at TEXT NOT NULL DEFAULT ''")


        for key, value in DEFAULT_SITE_SETTINGS.items():
            conn.execute(
                """
                INSERT INTO site_settings(key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO NOTHING
                """,
                (key, value),
            )

        # 内置接口以 API_PRESENTATION 为准（= API_CATALOG 全部 + douyin_parse，
        # 后者是单独登记在 API_PRESENTATION 里的），先按名单对账。
        # 下面的 INSERT ... ON CONFLICT 只增不删，所以路由被删掉之后老记录会一直
        # 留在库里 —— 门户就会把已经不存在的接口展示成可用（历史上 joke_random /
        # university_search 就是这么变成"幽灵接口"的，还各带着几百次调用记录）。
        #
        # 用 DELETE 而不是 enabled=0：ON CONFLICT DO UPDATE 不会重置 enabled，
        # 将来若路由恢复，停用标记会留下一个永远 403 的接口；而 DELETE 之后
        # 名单会把它重新插回默认启用状态。api_stats 里的历史调用记录不受影响
        # （它按 api_name 字符串记，不依赖这张表）。
        catalog_names = sorted(API_PRESENTATION)
        placeholders = ",".join("?" * len(catalog_names))
        stale = conn.execute(
            f"SELECT name FROM apis WHERE is_builtin = 1 AND name NOT IN ({placeholders})",
            catalog_names,
        ).fetchall()
        if stale:
            conn.execute(
                f"DELETE FROM apis WHERE is_builtin = 1 AND name NOT IN ({placeholders})",
                catalog_names,
            )
            logger.info(
                "清理了 %d 个不在内置名单中的接口记录：%s",
                len(stale),
                ", ".join(row["name"] for row in stale),
            )

        for item in API_CATALOG:
            conn.execute(
                """
                INSERT INTO apis(
                    name, path, title, description, category, method,
                    response_type, response_body, is_builtin, sort_order
                )
                VALUES (
                    :name, :path, :title, :description, :category, :method,
                    :response_type, :response_body, :is_builtin, :sort_order
                )
                ON CONFLICT(name) DO UPDATE SET
                    path = excluded.path,
                    title = excluded.title,
                    description = excluded.description,
                    category = excluded.category,
                    method = excluded.method,
                    response_type = excluded.response_type,
                    is_builtin = excluded.is_builtin,
                    sort_order = excluded.sort_order,
                    updated_at = CURRENT_TIMESTAMP
                """,
                item,
            )

        for pair in settings.default_api_keys.split(","):
            if not pair.strip():
                continue
            key, _, name = pair.partition(":")
            conn.execute(
                """
                INSERT INTO api_keys(key, name, created_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET name = excluded.name
                """,
                (key.strip(), name.strip() or key.strip()),
            )

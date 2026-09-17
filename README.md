# 绿夜API

基于 `FastAPI + SQLite` 的轻量 API 聚合门户，内置 30+ 公开接口、前端文档页、后台管理和动态自定义接口。

## 功能特性

- 30+ 内置公开接口（抖音解析、IP 查询、时间戳、哈希、Base64、UUID、随机密码/颜色/昵称、成语查询、唐诗、历史上的今天、占位图、二维码、必应每日图等）
- 纯前端接口测试台（`/test`），浏览器内直接调参试调
- 自动生成的接口文档页（`/doc/{name}.html`）
- 后台管理：接口 CRUD、启用/停用、Api-Key 管理、调用统计、访问日志导出、数据库备份
- 动态自定义接口：后台登记后自动挂载，支持 JSON/Text/HTML 响应模板
- SQLite 持久化，零外部依赖
- 限流、IP 白名单、弱口令校验、安全响应头、CSV 公式注入防护

## 目录结构

```text
main.py                  FastAPI 入口，门户路由与应用装配
admin/                   后台管理路由（登录、接口/Key/统计/日志/备份）
apis/
├── main.py              业务路由注册
├── data_loader.py       静态数据加载器
├── versioned.py         /api/v1 版本化兼容路由
├── data/                静态数据集（手机号段、成语、唐诗、历史上的今天等）
├── demo/                测试接口
├── divination/          易经占卜（含 iching.json 数据）
├── domain/              域名查询
├── douyin/              抖音无水印解析（a_bogus 签名）
├── dynamic/             动态自定义接口
├── freeapi/             免费 API 聚合
├── ip/                  IP 查询
├── phone/               手机号归属地
├── spider/              新闻/视频/图片爬虫聚合
├── time/                时间接口
├── tools/               工具类（哈希、Base64、UUID、密码、颜色、昵称等）
└── word/                随机短句 / 一言
core/                    配置、数据库、中间件、鉴权依赖、异常处理、路由索引
frontend/                前端页面（首页、文档、测试台、后台、注册）
static/                  后台静态资源
tests/                   pytest 测试套件
scripts/                 冒烟测试、数据修复、清理脚本
tools/                   数据集构建工具
deploy/                  systemd service、Nginx 配置示例
.github/workflows/       CI 配置
config.json.example      配置模板
```

## 快速启动

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config.json.example config.json
python main.py
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.json.example config.json
python main.py
```

默认地址：

```text
首页:     http://127.0.0.1:8000/
测试台:   http://127.0.0.1:8000/test
注册页:   http://127.0.0.1:8000/register
后台:     http://127.0.0.1:8000/manage-api
Swagger:  http://127.0.0.1:8000/docs
```

默认凭据（**仅本地开发使用**）：

```text
Admin-Token: admin888
Api-Key: test123
```

> 服务一旦监听非回环地址（如 `0.0.0.0`），启动日志会打印安全告警；
> `environment` 为 `production` 时则直接拒绝启动。

## 配置

项目统一使用 `config.json`，从 `config.json.example` 复制后修改即可。

### 生产环境

生产环境请直接编辑 `config.json`，至少修改以下字段：

```json
{
  "environment": "production",
  "host": "0.0.0.0",
  "admin_token": "请替换成强随机字符串",
  "default_api_keys": "请替换成强随机 key:默认用户",
  "allow_self_register": false,
  "admin_public_path": "/manage-api",
  "rate_limit_per_minute": 120
}
```

关键配置项说明：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `environment` | `development` | 设为 `production` 启用强校验、Secure Cookie、HSTS |
| `admin_token` | `admin888` | 后台登录口令，生产必须替换 |
| `default_api_keys` | `test123:测试用户` | 初始 Api-Key，生产必须替换 |
| `require_api_key` | `false` | 设为 `true` 则所有接口必须传 Api-Key |
| `allow_self_register` | `true` | 是否允许公开自助注册 Key |
| `admin_ip_allowlist` | 空 | 逗号分隔的 IP，仅允许这些 IP 访问后台 |
| `admin_public_path` | `/manage-api` | 后台路径，可改冷门路径减少扫描 |
| `rate_limit_per_minute` | `120` | 单 IP 每分钟请求上限，0 为不限 |
| `enable_douyin` | `true` | 是否启用抖音解析接口 |

> ⚠️ **`environment=production` 必须配合 HTTPS**：该模式下后台 Cookie 会带
> `Secure` 属性，用纯 HTTP 访问时浏览器不会保存它，表现为"登录成功但一直是未登录状态"。

弱口令校验以"是否对外监听"为准：只要 `host` 不是 `127.0.0.1`/`localhost`，
使用默认凭据就会告警；`environment=production` 时直接启动失败。

### 环境变量覆盖

`config.json` 里的任意字段都可以用 `API_PLATFORM_<字段名大写>` 覆盖，无需改文件：

```bash
# 让冒烟脚本走独立临时库
API_PLATFORM_DATABASE_PATH=./data/smoke.sqlite3 python scripts/smoke_test.py

# 临时换后台口令
API_PLATFORM_ADMIN_TOKEN=xxx python main.py
```

## 主要路由

```text
GET  /                      首页
GET  /test                  接口测试台
GET  /register              注册页
POST /register/key          自助生成 Key
GET  /portal/apis           接口目录（含分类、调用统计）
GET  /portal/apis/{name}    单个接口详情
GET  /doc/{name}.html       接口文档页
GET  /manage-api            后台页面
POST /manage-api/login      后台登录
GET  /health                健康检查
```

内置接口均挂在 `/api/` 下，完整列表启动后访问 `/portal/apis` 或 `/docs` 查看。

## 静态数据

数据集统一放在 `apis/data/`，路由文件只保留逻辑：

| 文件 | 大小 | 用途 |
|------|------|------|
| `phone_prefix.json` | ~7.3MB | 手机号段归属地 |
| `idioms.json` | ~4.6MB | 成语词典 |
| `history_today.json` | ~2.5MB | 历史上的今天 |
| `poetry_tang.json` | ~1.7MB | 唐诗 |
| `yiyan.txt` | ~636KB | 一言句子库 |
| `words.txt` | ~225KB | 随机短句库 |
| `spider.json` | ~3KB | 爬虫聚合配置 |
| `phone_map.json` | ~0.5KB | 手机号段映射 |
| `nickname_prefixes.txt` | — | 昵称前缀 |
| `nickname_suffixes.txt` | — | 昵称后缀 |

另有 `apis/divination/data/iching.json`（易经六十四卦数据）。

## 后台能力

后台路径默认 `/manage-api`（可通过 `admin_public_path` 修改），支持：

- 接口 CRUD 与启用/停用
- Api-Key 管理（创建、停用、删除、每日额度）
- 调用统计（按接口、按 Key 分组）
- 访问日志查询与 CSV 导出（含公式注入防护）
- 抖音解析健康状态（连续失败次数监控）
- 数据库备份下载
- 路由巡检（标记数据库中已失效的幽灵接口）

## 测试

```bash
python -m pytest -q
```

测试**不会**碰真实数据库：`tests/conftest.py` 在导入应用前把 `database_path`
指向临时目录，会话结束后自动删除。

冒烟测试：

```bash
python scripts/smoke_test.py        # 基础端点
python scripts/smoke_spider_apis.py # 爬虫相关接口
```

## 部署

完整部署说明见 [DEPLOY.md](DEPLOY.md)。

### Docker Compose（推荐）

```bash
cd /opt
git clone https://github.com/sanmu1019/api-platform.git
cd api-platform
cp config.json.example config.json
mkdir -p data
# 编辑 config.json，填入生产配置（见上文）
docker compose up -d --build
```

容器以非 root 用户（UID 10001）运行，挂载的 `data/` 目录需确保可写：

```bash
sudo chown -R 10001:10001 data
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

### Nginx 反向代理

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/api-platform
sudo nano /etc/nginx/sites-available/api-platform   # 修改 server_name
sudo ln -s /etc/nginx/sites-available/api-platform /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

HTTPS（Let's Encrypt）：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名
```

### 运维

```bash
# 升级
cd /opt/api-platform
git pull
docker compose up -d --build

# 日志
docker compose logs -f

# 需备份的数据
config.json
data/
```

## License

[MIT](LICENSE) © 2026 sanmu1019

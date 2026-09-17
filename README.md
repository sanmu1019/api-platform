# 绿夜API

基于 `FastAPI + SQLite` 的轻量 API 门户，包含：

- 公开接口集合
- 简单的前端文档页
- 后台接口管理
- 动态自定义接口
- SQLite 持久化

## 目录结构

```text
main.py                 FastAPI 入口
admin/                  后台接口
apis/                   内置业务接口
apis/data/              静态数据文件
core/                   配置、数据库、中间件、依赖
frontend/               前端页面和文档页
static/                 静态资源
tests/                  测试
deploy/                 部署示例
config.json.example     配置模板
```

## 快速启动

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy config.json.example config.json
python main.py
```

默认地址：

```text
首页:    http://127.0.0.1:8000/
注册页:  http://127.0.0.1:8000/register
后台:    http://127.0.0.1:8000/manage-api
Swagger: http://127.0.0.1:8000/docs
```

默认凭据（**仅本地开发使用**）：

```text
Admin-Token: admin888
Api-Key: test123
```

> 这两个值是公开的默认值。服务一旦监听非回环地址（如 `0.0.0.0`），
> 启动日志会打印安全告警；`environment` 为 `production` 时则直接拒绝启动。

## 配置

项目统一使用 `config.json`。本地开发直接复制模板即可：

```bash
cp config.json.example config.json
```

### 生产环境

仓库里另有一份已经配好强随机凭据的生产配置 `config.production.json`
（已被 `.gitignore` / `.dockerignore` 排除，不会进版本库和镜像）：

```bash
# 上传到服务器后直接使用
cp config.production.json config.json
```

它相对模板做了这些收紧：

| 配置项 | 值 | 原因 |
|--------|-----|------|
| `environment` | `production` | 启用启动期强校验、Secure Cookie、HSTS |
| `admin_token` | 强随机 32 字节 | 替换默认 `admin888` |
| `default_api_keys` | 强随机 key | 替换默认 `test123` |
| `allow_self_register` | `false` | 关闭公开自助注册 |
| `show_admin_entry` | `false` | 首页不展示后台入口 |

> ⚠️ **`environment=production` 必须配合 HTTPS**：该模式下后台 Cookie 会带
> `Secure` 属性，用纯 HTTP 访问时浏览器不会保存它，表现为"登录成功但一直是未登录状态"。
> 请先按 [DEPLOY.md](DEPLOY.md) 用 Nginx + certbot 配好 HTTPS。

生产环境手工改配置时至少要改这些字段：

```json
{
  "environment": "production",
  "host": "0.0.0.0",
  "admin_token": "请替换成强随机字符串",
  "default_api_keys": "请替换成强随机 key:默认用户",
  "admin_public_path": "/manage-api",
  "show_admin_entry": false,
  "allow_self_register": false,
  "rate_limit_per_minute": 120
}
```

弱口令校验以"是否对外监听"为准：只要 `host` 不是 `127.0.0.1`/`localhost`，
使用默认凭据就会告警；`environment=production` 时直接启动失败。

## 主要接口

```text
GET  /                      首页
GET  /register              注册页
POST /register/key          自助生成 key
GET  /portal/apis           接口目录数据
GET  /portal/apis/{name}    单个接口详情数据
GET  /doc/{name}.html       单个接口文档页
GET  /manage-api            后台页面
GET  /health                健康检查
```

## 数据组织规则

现在静态数据不再直接堆在 `route.py` 中：

- 纯字符串列表：用 `txt`
- 有结构字段的数据：用 `json`
- 路由文件只保留接口逻辑

当前已经迁移到 `apis/data/` 的包括：

- `yiyan.txt`
- `words.txt`
- `nickname_prefixes.txt`
- `nickname_suffixes.txt`
- `phone_map.json`
- `spider.json`

## 文档页与在线调试

接口详情页位于：

```text
/doc/{name}.html
```

当前文档页支持：

- 请求示例展示
- 常见参数说明
- 在线调试
- 路径参数替换

例如：

```text
http://127.0.0.1:8000/doc/idiom_search.html
```

## 后台能力

后台路径默认是：

```text
/manage-api
```

支持：

- 接口 CRUD
- 启用 / 停用接口
- Api-Key 管理
- 调用统计
- 访问日志导出
- 数据库备份
- 动态接口模板

## 测试

运行测试：

```bash
python -m pytest -q
```

如果当前环境还没装 `pytest`，先执行：

```bash
pip install -r requirements.txt
```

测试**不会**碰你的真实数据库：`tests/conftest.py` 会在导入应用之前，把
`database_path` 指向一个临时目录，会话结束后自动删除。

### 用环境变量覆盖配置

`config.json` 里的任意字段都可以用 `API_PLATFORM_<字段名大写>` 覆盖，
无需改文件（容器 / CI 里尤其方便）：

```bash
# 让冒烟脚本也走独立的临时库，不污染真实数据
API_PLATFORM_DATABASE_PATH=./data/smoke.sqlite3 python scripts/smoke_test.py

# 临时换个后台口令
API_PLATFORM_ADMIN_TOKEN=xxx python main.py
```

## 部署

完整部署说明见 [DEPLOY.md](DEPLOY.md)。VPS 上推荐使用 Docker Compose 部署，再用 Nginx 做反向代理。
如果部署到 Android Termux，请参阅 [TERMUX.md](TERMUX.md)；该方式直接运行 FastAPI，不需要 Docker。

### VPS Docker Compose 部署

以 Ubuntu / Debian 为例，先安装基础依赖：

```bash
sudo apt update
sudo apt install -y git docker.io docker-compose-plugin nginx
sudo systemctl enable --now docker nginx
```

拉取项目并准备配置：

```bash
cd /opt
sudo git clone <你的仓库地址> api-platform
cd /opt/api-platform
cp config.json.example config.json
mkdir -p data
```

编辑 `config.json`，生产环境至少修改：

```json
{
  "environment": "production",
  "host": "0.0.0.0",
  "port": 8000,
  "database_path": "./data/api_platform.sqlite3",
  "admin_token": "请替换成强随机后台 token",
  "default_api_keys": "请替换成强随机 api-key:默认用户",
  "allow_self_register": false,
  "admin_public_path": "/manage-api",
  "show_admin_entry": false
}
```

生产环境不要使用默认的 `admin888`、`test123`、`please-change-admin-token` 或 `please-change-api-key`，否则启动时会被安全校验拦截。

启动服务：

```bash
docker compose up -d --build
docker compose logs -f
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

### Nginx 反向代理

复制并修改示例配置：

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/api-platform
sudo nano /etc/nginx/sites-available/api-platform
```

把 `server_name example.com;` 改成你的域名，然后启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/api-platform /etc/nginx/sites-enabled/api-platform
sudo nginx -t
sudo systemctl reload nginx
```

配置 HTTPS：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com
```

### 运维命令

升级：

```bash
cd /opt/api-platform
git pull
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

需要备份的关键数据：

```text
config.json
data/
```

常用地址：

```text
首页:    https://你的域名/
后台:    https://你的域名/manage-api
健康:    https://你的域名/health
Swagger: https://你的域名/docs
```

## License

[MIT](LICENSE) © 2026 mylyve

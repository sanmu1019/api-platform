# 绿夜API 部署指南

## 项目简介
绿夜API是一个FastAPI开发的API聚合平台，提供短视频无水印解析、开发者工具、内容聚合等接口。

---

## 1. 准备配置

如果你本地已经存有一份配好强随机凭据的生产配置，可以直接复用：

```bash
cp config.production.json config.json
```

> ⚠️ `config.production.json` **不在仓库里**（已被 `.gitignore` 与 `.dockerignore`
> 排除，因为它含真实凭据）。**克隆仓库后没有这个文件**，请改用下面的模板方式。

或者从模板开始手工配置：

```bash
cp config.json.example config.json
```

至少修改这些字段：

```json
{
  "environment": "production",
  "host": "0.0.0.0",
  "admin_token": "请替换成强随机字符串",
  "default_api_keys": "请替换成强随机 key:默认用户",
  "admin_public_path": "/manage-api",
  "allow_self_register": false
}
```

> ⚠️ **`environment=production` 必须配合 HTTPS**：该模式下后台 Cookie 带 `Secure`
> 属性，纯 HTTP 访问时浏览器不会保存，表现为"登录成功但一直显示未登录"。
> 请先完成第 4 步的 Nginx + certbot，再切到 production。
>
> 弱口令校验以"是否对外监听"为准：只要 `host` 不是回环地址，用默认凭据就会在
> 启动日志里告警；`environment=production` 时直接拒绝启动。

## 2. Docker Compose 部署

容器以非 root 用户（UID 10001）运行，而 `docker-compose.yml` 会把宿主机的
`./data` 挂载进容器。挂载目录会覆盖镜像内的权限设置，所以**必须先让宿主机上的
`data` 目录归 UID 10001 所有**，否则容器内无法写入 SQLite：

```bash
mkdir -p data
sudo chown -R 10001:10001 data
```

启动：

```bash
docker compose up -d --build
docker compose logs -f
```

> 若启动日志出现 `unable to open database file` / `attempt to write a readonly database`，
> 基本都是这一步的权限没做。不想调整目录权限的话，删掉 `Dockerfile` 里的
> `useradd` 与 `USER appuser` 两段，容器会退回 root 运行。

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

升级：

```bash
git pull
docker compose up -d --build
```

## 3. systemd 部署

示例以 `/opt/api-platform` 为项目目录：

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin api
sudo mkdir -p /opt/api-platform
sudo chown -R api:api /opt/api-platform
```

安装依赖：

```bash
cd /opt/api-platform
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.json.example config.json
```

安装服务：

```bash
sudo cp deploy/api-platform.service /etc/systemd/system/api-platform.service
sudo systemctl daemon-reload
sudo systemctl enable --now api-platform
sudo systemctl status api-platform
```

查看日志：

```bash
journalctl -u api-platform -f
```

## 4. Nginx 反向代理

复制示例配置：

```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/api-platform
sudo ln -s /etc/nginx/sites-available/api-platform /etc/nginx/sites-enabled/api-platform
sudo nginx -t
sudo systemctl reload nginx
```

生产环境建议再用 `certbot` 配置 HTTPS。

## 5. 常用地址

```text
首页:   http://服务器:8000/
后台:   http://服务器:8000/manage-api
健康检查: http://服务器:8000/health
Swagger:  http://服务器:8000/docs
```

---

## 6. 接口说明

### 短视频解析类

| 接口 | 路径 | 需要代理 | 需要Cookie | 说明 |
|------|------|----------|------------|------|
| 通用视频解析 | `/api/parse/video?url=xxx` | 国外平台需要 | 部分平台需要 | 自动识别平台，支持上千个网站（基于yt-dlp） |
| 抖音解析 | `/api/douyin/parse?url=xxx` | 可选 | 不需要 | 抖音无水印解析 |
| 快手解析 | `/api/parse/kuaishou?url=xxx` | 不需要 | 不需要 | 快手无水印解析 |
| 皮皮虾解析 | `/api/parse/pipix?url=xxx` | 不需要 | 不需要 | 皮皮虾无水印解析 |
| 小红书解析 | `/api/parse/xhs?url=xxx` | 不需要 | **需要** | 小红书无水印解析 |
| 微博解析 | `/api/parse/video?url=xxx` | 不需要 | 不需要 | 微博视频/图片解析 |
| 西瓜视频解析 | `/api/parse/video?url=xxx` | 不需要 | 不需要 | 西瓜视频解析 |
| AcFun解析 | `/api/parse/video?url=xxx` | 不需要 | 不需要 | AcFun视频解析 |
| 视频号解析 | `/api/wxsph/parse?url=xxx` | 不需要 | **需要** | 微信视频号解析 |
| B站封面 | `/api/bilibili/cover?bvid=xxx` | 不需要 | 不需要 | B站视频封面 |
| TikTok解析 | `/api/parse/video?url=xxx` | **需要** | 不需要 | TikTok无水印解析 |
| YouTube解析 | `/api/parse/video?url=xxx` | **需要** | 不需要 | YouTube视频解析 |
| Twitter/X解析 | `/api/parse/video?url=xxx` | **需要** | 不需要 | Twitter视频解析 |

### 其他工具类
- 时间转换、哈希计算、Base64、UUID生成
- 二维码生成、拼音转换、数字大写
- 汇率查询、天气查询、节假日查询
- 万年历/老黄历、金价油价查询
- 段子/笑话/歇后语/土味情话/名人名言
- 热榜（微博/百度/GitHub/B站）
- 音乐搜索（QQ音乐/酷狗）
- 表情包搜索
- 手机号归属地、网站Whois

---

## 7. 代理与Cookie配置

### 代理配置
在 `config.json` 中添加：
```json
{
  "douyin_proxy": "http://127.0.0.1:7890"
}
```
- 国内平台（抖音/快手/皮皮虾/小红书/微博等）**不需要代理**，直连即可
- 国外平台（TikTok/YouTube/Twitter等）**需要配置代理**
- 代理格式：`http://IP:端口`

### Cookie配置
在 `config.json` 中添加：
```json
{
  "xiaohongshu_cookie": "你的小红书cookie",
  "wxsph_cookie": "你的视频号cookie"
}
```
- **小红书解析**：登录小红书网页版，从浏览器开发者工具的Network里复制Cookie
- **视频号解析**：从微信开发者工具或浏览器里复制视频号的Cookie
- Cookie会过期，过期了重新获取即可

---

## 8. 核心依赖
| 依赖 | 用途 |
|------|------|
| fastapi | Web框架 |
| uvicorn | ASGI服务器 |
| httpx | 异步HTTP请求 |
| fake-useragent | 随机UA |
| parsel | HTML解析 |
| yt-dlp | 通用视频解析（支持上千个平台） |
| chinesecalendar | 中国节假日 |
| lunar-python | 农历/老黄历 |
| pypinyin | 拼音转换 |

---

## 9. 安全建议
- 生产环境必须修改默认的 `admin_token` 和 `default_api_keys`
- 生产环境把 `environment` 设为 `production`
- 修改默认的后台路径 `admin_public_path`
- 配置 `cors_origins` 限制跨域来源

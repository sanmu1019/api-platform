# 部署指南

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

# 接口 curl 测试方式

本项目为公开 API 门户：

- `/api/*` 业务接口：当前配置 `require_api_key=false`，**不传 Api-Key 也可调用**；传了则会校验有效性并计入该 Key 的配额
- `/portal/*` 门户接口：无需鉴权
- `/manage-api/*` 后台接口：**必须**带 `Admin-Token` 请求头（或登录后的 `admin_token` Cookie），缺失返回 401

## 启动

```powershell
cd E:\api
.venv\Scripts\activate
pip install -r requirements.txt
copy config.json.example config.json
python main.py
```

默认地址：

```text
http://127.0.0.1:8000
```

凭据用你自己 `config.json` 里的值，下文统一写作占位符（不要把真实值写进文档或提交到仓库）：

```text
Admin-Token: YOUR_ADMIN_TOKEN
Api-Key:     YOUR_API_KEY
```

带 Key 调用示例（可选，`require_api_key=true` 时必须）：

```powershell
curl.exe -sS -H "Api-Key: YOUR_API_KEY" http://127.0.0.1:8000/api/ip
```

## 一键真实检查

```powershell
python .\scripts\curl_public_check.py
```

该脚本通过 `curl.exe` 请求真实服务，校验业务字段，不只是检查 HTTP 200。

## 健康检查

```powershell
curl.exe -sS http://127.0.0.1:8000/health
```

## 基础接口

```powershell
curl.exe -sS http://127.0.0.1:8000/api/v1/demo
curl.exe -sS http://127.0.0.1:8000/api/ip
curl.exe -sS http://127.0.0.1:8000/api/time
curl.exe -sS "http://127.0.0.1:8000/api/time?value=1700000000"
curl.exe -sS http://127.0.0.1:8000/api/phone/13800138000
curl.exe -sS http://127.0.0.1:8000/api/word/random
curl.exe -sS http://127.0.0.1:8000/api/version
```

> `/api/demo` 没有无版本路径，只有 `/api/v1/demo`。

### /api/v1 版本化路径

只有 demo / ip / time / phone / word / freeapi / tools / spider 这 8 个模块有 `/api/v1/*` 别名（见 API.md「版本化」），其他模块用 `/api/v1/...` 会 404。

```powershell
curl.exe -sS http://127.0.0.1:8000/api/v1/ip
curl.exe -sS "http://127.0.0.1:8000/api/v1/tool/hash?text=abc"
curl.exe -sS "http://127.0.0.1:8000/api/v1/poetry/tang?count=1"
```

## 免费 / 图片 / 媒体类接口

```powershell
curl.exe -sS http://127.0.0.1:8000/api/yiyan
curl.exe -sS "http://127.0.0.1:8000/api/avatar/random?seed=test"
curl.exe -sS "http://127.0.0.1:8000/api/short/hash?url=https://example.com"
curl.exe -sS "http://127.0.0.1:8000/api/bilibili/cover?bvid=BV1xx411c7mD"
curl.exe -sS http://127.0.0.1:8000/api/bing/daily
```

B 站视频代理返回的是视频流，建议落盘而不是打到终端：

```powershell
curl.exe -sS -o test.mp4 "http://127.0.0.1:8000/api/bilibili/proxy?bvid=BV1xx411c7mD&type=mp4"
```

错误参数示例：

```powershell
curl.exe -sS "http://127.0.0.1:8000/api/short/hash?url=ftp://example.com"
```

## 工具类接口

```powershell
curl.exe -sS "http://127.0.0.1:8000/api/tool/hash?text=abc&algorithm=sha256"
curl.exe -sS "http://127.0.0.1:8000/api/tool/base64?text=abc"
curl.exe -sS "http://127.0.0.1:8000/api/tool/uuid?count=2"
curl.exe -sS "http://127.0.0.1:8000/api/image/qrcode?text=hello"
```

### tools2 小工具

```powershell
curl.exe -sS "http://127.0.0.1:8000/api/tools2/carplate?code=%E4%BA%ACA"
curl.exe -sS "http://127.0.0.1:8000/api/tools2/answer?question=test"
curl.exe -sS http://127.0.0.1:8000/api/tools2/food
curl.exe -sS "http://127.0.0.1:8000/api/tools2/luck?name=test"
curl.exe -sS "http://127.0.0.1:8000/api/tools2/earthquake?limit=3"
```

## 内容 / 爬虫风格接口

```powershell
curl.exe -sS http://127.0.0.1:8000/api/history/today
curl.exe -sS "http://127.0.0.1:8000/api/idiom/search?keyword=%E7%B2%BE"
curl.exe -sS "http://127.0.0.1:8000/api/poetry/tang?keyword=%E6%9D%8E%E7%99%BD"
curl.exe -sS http://127.0.0.1:8000/api/joke/random
```

### extra 趣味文案

```powershell
curl.exe -sS http://127.0.0.1:8000/api/extra/xiehouyu/random
curl.exe -sS http://127.0.0.1:8000/api/extra/renwen/random
curl.exe -sS http://127.0.0.1:8000/api/extra/tuwei/random
curl.exe -sS http://127.0.0.1:8000/api/extra/dujitang/random
curl.exe -sS http://127.0.0.1:8000/api/extra/mingren/random
curl.exe -sS "http://127.0.0.1:8000/api/extra/pinyin?text=%E4%BD%A0%E5%A5%BD"
curl.exe -sS "http://127.0.0.1:8000/api/extra/number/upper?number=1234.56"
curl.exe -sS "http://127.0.0.1:8000/api/extra/convert/zh?text=%E6%BC%A2%E5%AD%97&mode=to_jian"
curl.exe -sS "http://127.0.0.1:8000/api/extra/dream?keyword=%E6%B0%B4"
curl.exe -sS "http://127.0.0.1:8000/api/extra/ping?host=baidu.com"
```

## 热榜 / 汇率 / 天气 / 日历 / 行情

```powershell
curl.exe -sS "http://127.0.0.1:8000/api/hot/weibo?limit=5"
curl.exe -sS "http://127.0.0.1:8000/api/exchange/rate?from=USD&to=CNY"
curl.exe -sS "http://127.0.0.1:8000/api/exchange/convert?from=EUR&to=JPY&amount=100"
curl.exe -sS "http://127.0.0.1:8000/api/weather/current?city=%E5%8C%97%E4%BA%AC"
curl.exe -sS "http://127.0.0.1:8000/api/holiday/check?date=2026-10-01"
curl.exe -sS "http://127.0.0.1:8000/api/lunar/day?date=2026-10-01"
curl.exe -sS http://127.0.0.1:8000/api/price/gold
curl.exe -sS http://127.0.0.1:8000/api/price/silver
curl.exe -sS http://127.0.0.1:8000/api/price/oil
```

## 音乐搜索

设置了 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量时会走代理。

```powershell
curl.exe -sS "http://127.0.0.1:8000/api/music/qq/search?keyword=%E6%99%B4%E5%A4%A9&limit=3"
curl.exe -sS "http://127.0.0.1:8000/api/music/kugou/search?keyword=%E6%99%B4%E5%A4%A9&limit=3"
```

## 占卜 / 域名接口

```powershell
curl.exe -sS "http://127.0.0.1:8000/api/divination/plum?question=%E6%B5%8B%E8%AF%95&year=2026&month=9&day=16&hour=10"
curl.exe -sS "http://127.0.0.1:8000/api/divination/number?number=258"

curl.exe -sS "http://127.0.0.1:8000/api/domain/whois?domain=baidu.com"
curl.exe -sS "http://127.0.0.1:8000/api/domain/icp?domain=baidu.com"
curl.exe -sS "http://127.0.0.1:8000/api/domain/info?domain=github.com"
```

## 抖音解析

### GET query

注意 `--data-urlencode` 必须写成 `url=完整分享文本`。

```powershell
curl.exe -sS -G "http://127.0.0.1:8000/api/douyin/parse" `
  --data-urlencode "url=https://v.douyin.com/你的短链/" `
  --data-urlencode "debug=true" `
  --data-urlencode "timeout=10"
```

### 只探测短链

```powershell
curl.exe -sS -G "http://127.0.0.1:8000/api/douyin/parse" `
  --data-urlencode "url=https://v.douyin.com/你的短链/" `
  --data-urlencode "probe=true" `
  --data-urlencode "timeout=6"
```

### POST JSON

```powershell
curl.exe -sS -X POST "http://127.0.0.1:8000/api/douyin/parse" `
  -H "Content-Type: application/json" `
  --data "{\"url\":\"https://v.douyin.com/你的短链/\",\"debug\":true,\"timeout\":10}"
```

> 抖音接口可能触发风控或链接失效，此时返回 400 并附诊断信息，属正常行为。

## 视频号 / 通用短视频解析

视频号解析需要先配置 `wxsph_cookie`（`config.json`）或环境变量 `WXSPH_COOKIE`，否则返回 500。

```powershell
curl.exe -sS -G "http://127.0.0.1:8000/api/wxsph/parse" `
  --data-urlencode "url=https://weixin.qq.com/sph/你的分享ID"

curl.exe -sS -G "http://127.0.0.1:8000/api/parse/video" `
  --data-urlencode "url=你的短视频分享链接"
```

> 皮皮虾、小红书等平台都走 `/api/parse/video`，没有 `/api/parse/kuaishou`、`/api/parse/pipix`、`/api/parse/xhs` 这类按平台拆分的路径。

## 动态自定义接口

先在后台创建自定义接口（`name` 即 slug），然后两条路径都能访问，鉴权规则与内置接口相同：

```powershell
curl.exe -sS http://127.0.0.1:8000/api/your-slug
curl.exe -sS http://127.0.0.1:8000/api/custom/your-slug
curl.exe -sS -H "Api-Key: YOUR_API_KEY" http://127.0.0.1:8000/api/custom/your-slug
```

不存在返回 404，已停用 403，请求方法与后台配置不一致返回 405。

## 门户和后台

```powershell
curl.exe -sS http://127.0.0.1:8000/portal/apis
curl.exe -sS http://127.0.0.1:8000/portal/apis/demo
```

后台接口需要 `Admin-Token`（后台路径默认 `/manage-api`，改过 `admin_public_path` 的请替换）：

```powershell
curl.exe -sS -H "Admin-Token: YOUR_ADMIN_TOKEN" http://127.0.0.1:8000/manage-api/session
curl.exe -sS -H "Admin-Token: YOUR_ADMIN_TOKEN" http://127.0.0.1:8000/manage-api/apis
curl.exe -sS -H "Admin-Token: YOUR_ADMIN_TOKEN" http://127.0.0.1:8000/manage-api/categories
curl.exe -sS -H "Admin-Token: YOUR_ADMIN_TOKEN" http://127.0.0.1:8000/manage-api/route-check
curl.exe -sS -H "Admin-Token: YOUR_ADMIN_TOKEN" http://127.0.0.1:8000/manage-api/keys
curl.exe -sS -H "Admin-Token: YOUR_ADMIN_TOKEN" http://127.0.0.1:8000/manage-api/stats
curl.exe -sS -H "Admin-Token: YOUR_ADMIN_TOKEN" "http://127.0.0.1:8000/manage-api/access-logs?limit=20"
```

登录（成功后设置 `admin_token` Cookie）：

```powershell
curl.exe -sS -X POST "http://127.0.0.1:8000/manage-api/login" `
  -H "Content-Type: application/json" `
  --data "{\"token\":\"YOUR_ADMIN_TOKEN\"}"
```

不带 token 会返回 401。

## 上传服务器前建议检查

```powershell
python -m pytest -q
python .\scripts\curl_public_check.py
curl.exe -sS http://127.0.0.1:8000/health
```

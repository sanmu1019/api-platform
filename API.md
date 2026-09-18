# 绿夜API 接口文档

> 基础地址：`http://你的域名`  
> 所有公开接口默认免鉴权，返回格式统一为 `{"code": 200, "msg": "success", "data": ...}`  
> 所有 `/api/*` 接口同时支持 `/api/v1/*` 版本化路径

---

## 目录

- [基础服务](#基础服务)
- [网络工具](#网络工具)
- [内容服务](#内容服务)
- [文案服务](#文案服务)
- [工具服务](#工具服务)
- [图片服务](#图片服务)
- [媒体服务](#媒体服务)
- [短视频解析](#短视频解析)
- [爬虫聚合](#爬虫聚合)
- [占卜服务](#占卜服务)
- [域名服务](#域名服务)
- [动态自定义接口](#动态自定义接口)
- [系统服务](#系统服务)
- [门户与页面](#门户与页面)
- [后台管理](#后台管理)
- [通用说明](#通用说明)

---

## 基础服务

### 测试接口

```
GET /api/demo
```

返回一段测试文本，用于验证服务是否正常。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": "这是一个测试接口"}
```

---

### IP 查询

```
GET /api/ip
```

返回客户端 IP 地址。自动识别 `X-Forwarded-For` / `X-Real-IP` 代理头。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"ip": "127.0.0.1"}}
```

---

### 时间接口

```
GET /api/time
```

返回当前 Unix 时间戳和格式化时间。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"timestamp": 1789689674, "datetime": "2026-09-18 08:01:14"}}
```

---

## 网络工具

### 手机号归属地

```
GET /api/phone/{phone}
```

根据手机号前 7 位号段查询归属地和运营商。内置 51 万条 7 位号段数据。

**路径参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phone | string | 是 | 11 位手机号，格式 `1[3-9]xxxxxxxxx` |

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "phone": "13800138000",
    "prefix": "138",
    "isp": "中国移动",
    "province": "北京",
    "city": "北京",
    "known": true,
    "note": "号段仅供参考，携号转网后可能与实际运营商不符"
  }
}
```

**错误：** 手机号格式不正确返回 `400`。

---

## 内容服务

### 随机短句

```
GET /api/word/random
```

从本地短句库随机返回一条中文短句。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"word": "生而为人，我很抱歉"}}
```

---

### 历史上的今天

```
GET /api/history/today?date=09-18
```

按 `MM-DD` 返回历史事件。内置全年 366 天、31622 条事件数据。不传 date 则使用当天日期。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date | string | 否 | 格式 `MM-DD`，如 `09-18` |

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "date": "09-18",
    "events": ["事件1", "事件2", "..."],
    "available": true,
    "covered_dates": 366,
    "source": "local"
  }
}
```

---

### 成语查询

```
GET /api/idiom/search?keyword=画蛇添足&limit=20
```

按成语词条或拼音检索，**不检索释义**。内置 30895 条成语数据。精确匹配排在最前。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| keyword | string | 是 | — | 关键词，1-20 字符 |
| limit | int | 否 | 20 | 返回条数，1-200 |

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {"word": "画蛇添足", "pinyin": "huà shé tiān zú", "explain": "画蛇时给蛇添上脚..."}
  ],
  "matched": 1,
  "exact": true,
  "pool_size": 30895
}
```

---

### 唐诗接口

```
GET /api/poetry/tang?keyword=月&count=1
```

返回唐诗，支持按标题/作者/内容关键词筛选。内置 6306 首唐诗。关键词无命中时回退随机返回，并标记 `fallback: true`。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| keyword | string | 否 | — | 关键词，匹配标题/作者/内容 |
| count | int | 否 | 1 | 返回条数，1-10 |

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {"title": "恩赐乐游园宴应制", "author": "张九龄", "content": "宝筵延厚命..."}
  ],
  "pool_size": 6306,
  "matched": 1434,
  "fallback": false
}
```

---

## 文案服务

### 随机一言

```
GET /api/yiyan
```

从一言库随机返回一句中文短句。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"text": "我要这天，再遮不住我眼..."}}
```

---

### 随机昵称

```
GET /api/tool/nickname
```

随机生成中文昵称（前缀 + 后缀 + 两位数字）。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"nickname": "南栀逐风77"}}
```

---

## 工具服务

### 时间戳转换

```
GET /api/tool/timestamp?value=1700000000
```

将 Unix 时间戳转为格式化时间。不传参数返回当前时间。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| value | int | 否 | Unix 时间戳（秒） |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"timestamp": 1700000000, "datetime": "2023-11-15 06:13:20"}}
```

**错误：** 超出可表示范围返回 `400`。

---

### 哈希计算

```
GET /api/tool/hash?text=hello&algorithm=md5
```

支持 md5、sha1、sha256、sha512 文本哈希。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| text | string | 是 | — | 待哈希文本 |
| algorithm | string | 否 | md5 | md5 / sha1 / sha256 / sha512 |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"algorithm": "sha256", "text": "hello", "hash": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"}}
```

**错误：** 不支持的算法返回 `400`。

---

### Base64 编解码

```
GET /api/tool/base64?text=hello&mode=encode
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| text | string | 是 | — | 待处理文本 |
| mode | string | 否 | encode | encode / decode |

**响应示例（encode）：**
```json
{"code": 200, "msg": "success", "data": {"mode": "encode", "input": "hello", "result": "aGVsbG8="}}
```

**响应示例（decode）：**
```json
{"code": 200, "msg": "success", "data": {"mode": "decode", "input": "aGVsbG8=", "result": "hello"}}
```

**错误：** 解码失败返回 `400`。

---

### UUID 生成

```
GET /api/tool/uuid?count=3
```

批量生成 UUID v4。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| count | int | 否 | 1 | 生成数量，1-50 |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"count": 3, "items": ["72917bfd-...", "..."]}}
```

---

### 随机密码

```
GET /api/tool/password?length=20&symbols=true
```

生成指定长度的随机密码，包含大小写字母 + 数字，可选特殊符号。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| length | int | 否 | 16 | 密码长度，6-64 |
| symbols | bool | 否 | true | 是否包含特殊符号 |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"length": 20, "password": "ArBcEg!z&jC@!D1^AXi7"}}
```

---

### 随机颜色

```
GET /api/tool/color
```

生成随机 HEX 和 RGB 颜色。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"hex": "#6743d0", "rgb": [103, 67, 208]}}
```

---

### 短码生成

```
GET /api/short/hash?url=https://example.com/test
```

根据 URL 在本地生成稳定短码（sha256 + urlsafe base64 前 10 位），不做跳转存储。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | string | 是 | 必须以 http:// 或 https:// 开头 |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"url": "https://example.com/test", "short_code": "m4-HI5oTdg"}}
```

---

## 图片服务

### 随机头像

```
GET /api/avatar/random?seed=test&style=adventurer
```

根据 seed 生成 DiceBear 随机头像 URL，不在服务端下载图片。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| seed | string | 否 | 随机 | 固定 seed 得到固定头像 |
| style | string | 否 | adventurer | DiceBear 风格，自动过滤非法字符 |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"seed": "test", "style": "adventurer", "url": "https://api.dicebear.com/9.x/adventurer/svg?seed=test"}}
```

---

### 占位图 URL

```
GET /api/image/placeholder?width=300&height=200&text=API
```

生成指定尺寸的 placehold.co 占位图 URL。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| width | int | 否 | 600 | 宽度，1-3000 |
| height | int | 否 | 400 | 高度，1-3000 |
| text | string | 否 | API | 占位图文字 |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"width": 300, "height": 200, "text": "API", "url": "https://placehold.co/300x200?text=API"}}
```

---

### 二维码 URL

```
GET /api/image/qrcode?text=hello&size=220
```

根据文本生成二维码图片 URL（qrserver.com）。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| text | string | 是 | — | 二维码内容，不能为空 |
| size | int | 否 | 220 | 尺寸，80-800 |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"text": "hello world", "size": 220, "url": "https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=hello%20world"}}
```

---

### 必应每日图

```
GET /api/bing/daily
```

获取必应每日图片信息。网络失败时返回兜底图片，不会 500。

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "title": "穿越山口腹地",
    "url": "https://www.bing.com/th?id=OHR.WinnatsPassPeak_...jpg",
    "copyright": "温纳茨山口，峰区国家公园，英格兰",
    "date": "20260918",
    "source": "bing"
  }
}
```

---

## 媒体服务

### B站封面信息

```
GET /api/bilibili/cover?bvid=BV1GJ411x7h7
```

调用 B 站公开接口返回视频标题、封面、作者、时长等信息。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bvid | string | 是 | BV 号，格式 `BV[0-9A-Za-z]{8,20}` |

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "bvid": "BV1GJ411x7h7",
    "title": "【官方 MV】Never Gonna Give You Up - Rick Astley",
    "cover": "http://i0.hdslb.com/bfs/archive/...jpg",
    "author": "Rick Astley",
    "duration": 213,
    "pubdate": 1336863600,
    "source": "bilibili"
  }
}
```

**错误：** BV 号格式错误 `400`；视频不存在 `404`；上游请求失败 `502`。

---

## 短视频解析

### 抖音无水印解析

```
GET|POST /api/douyin/parse?url=https://v.douyin.com/xxx&timeout=6
```

抖音去水印解析，支持图文、短视频，支持分享短链接。通过官方详情接口（`/aweme/v1/web/aweme/detail/` + a_bogus 签名 + ttwid）获取无水印地址。可通过 `enable_douyin` 配置关闭。

> **⚠️ 国内网络需要代理**：抖音对国内服务器 IP 有风控，直连详情接口会返回 403。在 `config.json` 中配置 `douyin_proxy`（如 `"http://127.0.0.1:7890"`）即可走代理解析。解析失败时错误信息会提示是否已配置代理。

**如何配置代理：**

1. 打开项目根目录的 `config.json`（从 `config.json.example` 复制一份）
2. 在 `enable_douyin` 下方添加一行：`"douyin_proxy": "http://127.0.0.1:7890"`
3. 值填你的代理地址，支持 HTTP/HTTPS 代理（如 Clash 默认 `http://127.0.0.1:7890`、V2Ray 默认 `http://127.0.0.1:10809`）
4. 保存后重启服务（`python main.py`）
5. 调用接口时加 `debug=true`，响应的 `debug.proxy` 字段会显示当前使用的代理地址，确认是否生效

配置示例：
```json
{
  "enable_douyin": true,
  "douyin_proxy": "http://127.0.0.1:7890"
}
```

**查询参数 / POST Body（JSON）：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| url / text | string | 是 | — | 抖音分享链接或包含链接的完整分享文本 |
| timeout | float | 否 | 6.0 | 服务端请求超时，2-20 秒 |
| debug | bool | 否 | false | 返回详细诊断信息（含代理状态、详情接口失败原因） |
| probe | bool | 否 | false | 只探测链接和页面摘要，不强制解析 |

**响应示例（成功）：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "title": "视频标题",
    "author": {"nickname": "作者昵称", "avatar": "https://..."},
    "cover": "https://...",
    "video_url": "https://无水印视频地址",
    "duration": 74600,
    "music": {"title": "背景音乐", "url": "https://..."},
    "images": [],
    "source": "detail_api"
  }
}
```

**错误：** 缺少 url 返回 `400`；详情接口失败或风控返回 `400`，错误信息含详情接口失败原因和代理状态。debug 模式返回完整诊断信息。

## 热榜聚合

实时抓取多平台热榜，数据缓存 5 分钟。GitHub Trending 国内直连超时，需配置 `douyin_proxy` 代理。

### 平台列表

```
GET /api/hot/platforms
```

返回支持的热榜平台。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": [{"key": "weibo", "name": "微博热搜"}, {"key": "baidu", "name": "百度热搜"}, "..."]}
```

---

### 平台热榜

```
GET /api/hot/{platform}?limit=20
```

获取指定平台的热榜。

**路径参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| platform | string | 是 | 平台标识：`weibo` / `baidu` / `github` / `bilibili` |

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| limit | int | 否 | 20 | 返回条数，1-50 |

**各平台返回字段：**

| 平台 | 字段 |
|------|------|
| weibo | rank, title, hot(热度值), url, tag(热/新/沸) |
| baidu | rank, title, hot(热度值), url, desc |
| github | rank, title(owner/repo), url, desc |
| bilibili | rank, title, up(UP主), play(播放量), url, pic(封面) |

**响应示例（微博）：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "platform": "weibo",
    "name": "微博热搜",
    "count": 3,
    "items": [
      {"rank": 1, "title": "示例热搜", "hot": 2410189, "url": "https://s.weibo.com/...", "tag": "热"}
    ],
    "cached": true
  }
}
```

**错误：** 不支持的 platform 返回 `400`；上游抓取失败且无缓存时返回 `502`。

> **代理配置：** GitHub Trending 需在 `config.json` 中设置 `"douyin_proxy": "http://127.0.0.1:7890"`，与抖音解析共用代理。

---

## 汇率服务

基于 [Frankfurter](https://www.frankfurter.app/) 开源 API，数据来源欧洲央行（ECB），免 key，汇率缓存 1 小时。支持 30+ 主流货币。

### 货币列表

```
GET /api/exchange/currencies
```

返回支持的货币代码和名称。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": [{"code": "USD", "name": "United States Dollar"}, {"code": "CNY", "name": "Chinese Yuan"}], "count": 31}
```

---

### 汇率查询

```
GET /api/exchange/rate?from=USD&to=CNY&date=2026-09-18
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| from | string | 否 | USD | 源货币代码（3位大写） |
| to | string | 否 | CNY | 目标货币代码（3位大写） |
| date | string | 否 | 最新 | 历史日期 YYYY-MM-DD |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"from": "USD", "to": "CNY", "rate": 7.18, "date": "2026-09-17", "amount": 1}}
```

---

### 货币转换

```
GET /api/exchange/convert?from=EUR&to=JPY&amount=100
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| from | string | 否 | USD | 源货币代码 |
| to | string | 否 | CNY | 目标货币代码 |
| amount | float | 否 | 1.0 | 金额，须大于0 |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"from": "EUR", "to": "JPY", "amount": 100, "rate": 178.75, "result": 17875.0, "date": "2026-09-17"}}
```

---

## 天气服务

基于 [Open-Meteo](https://open-meteo.com/) 免 key API，CC BY 4.0 协议。天气数据缓存 10 分钟。

### 城市搜索

```
GET /api/weather/geo?name=北京
```

返回匹配城市的经纬度等信息，用于后续天气查询。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 城市名称（中文/英文均可） |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": [{"name": "Beijing", "latitude": 39.9042, "longitude": 116.4074, "country": "China", "admin1": "Beijing", "timezone": "Asia/Shanghai"}], "count": 1}
```

---

### 实时天气

```
GET /api/weather/current?latitude=39.9&longitude=116.4
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| latitude | float | 是 | 纬度（-90 到 90） |
| longitude | float | 是 | 经度（-180 到 180） |

**响应字段：** temperature(°C), apparent_temperature(体感), humidity(%), weather(中文天气描述), wind_speed(km/h), wind_direction(°), pressure(hPa)

---

### 多日预报

```
GET /api/weather/forecast?latitude=39.9&longitude=116.4&days=7
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| latitude | float | 是 | | 纬度 |
| longitude | float | 是 | | 经度 |
| days | int | 否 | 7 | 预报天数，1-16 |

**响应字段（每日）：** date, weather, temp_max, temp_min, precipitation(mm), wind_max, sunrise, sunset

---

## 节假日服务

基于 [chinesecalendar](https://github.com/LKI/chinese-calendar) 库，数据来源国务院公告，支持 2004-2026 年。

### 单日查询

```
GET /api/holiday/check?date=2026-10-01
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date | string | 是 | 日期 YYYY-MM-DD |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"date": "2026-10-01", "weekday": "Thursday", "is_workday": false, "is_holiday": true, "is_in_lieu": false, "holiday_name": "National Day"}}
```

---

### 范围查询

```
GET /api/holiday/range?start=2026-10-01&end=2026-10-07
```

返回范围内的节假日和调休上班日，最多查询 366 天。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start | string | 是 | 开始日期 YYYY-MM-DD |
| end | string | 是 | 结束日期 YYYY-MM-DD |

---

## 万年历服务

基于 [lunar-python](https://github.com/6tail/lunar-python) 纯算法库，零依赖，支持公历转农历、干支、生肖、节气、宜忌、吉神方位、星宿等。

### 当日黄历

```
GET /api/lunar/day?date=2026-10-01
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date | string | 是 | 公历日期 YYYY-MM-DD |

**响应字段：**

| 字段 | 说明 |
|------|------|
| solar | 公历日期、星期 |
| lunar | 农历年/月/日、完整表述 |
| ganzhi | 年月日时干支 |
| shengxiao | 生肖 |
| jieqi | 当前节气 |
| yi | 宜（列表） |
| ji | 忌（列表） |
| pengzu | 彭祖百忌（干/支） |
| chongsha | 冲煞 |
| nayin | 纳音（年/月/日） |
| lucky_directions | 吉神方位（喜神/福神/财神等） |
| taishen | 胎神占方 |
| xingxiu | 二十八星宿（名/禽/吉凶） |

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"lunar": {"full": "二〇二六年八月廿一"}, "ganzhi": {"year": "丙午", "month": "丁酉", "day": "戊申"}, "shengxiao": "马", "yi": ["冠笄", "沐浴", "出行"], "ji": ["嫁娶", "开市", "祭祀"]}}
```

---

## 行情服务

基于腾讯财经公开行情接口，免 key，数据缓存 5 分钟。覆盖国际黄金、白银、原油期货。

### 黄金行情

```
GET /api/price/gold
```

返回纽约黄金期货行情：price(最新价), change_pct(涨跌幅%), open, high, low, prev_close, time, date, unit(美元/盎司)

---

### 白银行情

```
GET /api/price/silver
```

返回纽约白银期货行情，单位：美元/盎司。

---

### 原油行情

```
GET /api/price/oil
```

返回 WTI 纽约原油期货行情，单位：美元/桶。

---

### 全部行情

```
GET /api/price/all
```

一次性返回黄金/白银/原油全部行情。

---

## 段子服务

内置 40+ 条中文段子数据集，纯本地随机，不依赖外部服务。可自行扩充 `apis/joke/jokes.json`。

### 随机段子

```
GET /api/joke/random
```

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"id": 3, "title": "面试", "content": "面试官：你最大的缺点是什么？..."}, "total": 40}
```

---

### 段子列表

```
GET /api/joke/list?page=1&page_size=10
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 10 | 每页数量，最大 50 |

---

### 段子详情

```
GET /api/joke/{id}
```

按 ID 获取单条段子，不存在返回 404。

---

## 占卜服务

### 梅花易数 · 时间起卦

```
GET /api/divination/plum?question=事业&year=2026&month=9&day=18&hour=8
```

不传时间参数则使用服务器当前时间。结果包含本卦、互卦、变卦、体用分析、动爻、应期。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question | string | 否 | 所问之事，仅用于回显，<=100 字 |
| year | int | 否 | 年，1900-2200 |
| month | int | 否 | 月，1-12 |
| day | int | 否 | 日，1-31 |
| hour | int | 否 | 时，0-23 |

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "question": "事业",
    "method": "time",
    "time": {"year": 2026, "month": 9, "day": 18, "hour": 8, "ganzhi": {...}},
    "hexagrams": {"ben": {...}, "hu": {...}, "bian": {...}},
    "analysis": {"body_gua": "...", "use_gua": "...", "moving_line": 3, "yingqi": 12, "fortune": "..."},
    "text": "完整解卦文本...",
    "disclaimer": "结果仅作传统文化娱乐参考，不构成任何建议"
  }
}
```

**错误：** 日期不存在（如 2月30日）返回 `400`。

---

### 梅花易数 · 数字起卦

```
GET /api/divination/number?number=258&question=财运&month=9&hour=8
```

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| number | int | 是 | 三位数字，100-999 |
| question | string | 否 | 所问之事，<=100 字 |
| month | int | 否 | 月，不传用当前月 |
| hour | int | 否 | 时，不传用当前小时；动爻取决于时辰 |

---

## 域名服务

### WHOIS 查询

```
GET /api/domain/whois?domain=github.com&timeout=10
```

查询域名 WHOIS 注册信息（注册人、邮箱、注册商、注册时间、到期时间、DNS、状态）。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| domain | string | 是 | — | 域名或完整 URL，3-253 字符 |
| timeout | float | 否 | 10.0 | 上游超时，2-25 秒 |

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "domain": "github.com",
    "available": true,
    "whois": {
      "注册人": "...",
      "邮箱": "...",
      "注册商网址": "...",
      "注册商": "MarkMonitor",
      "注册商来源": "推断自 registrar_url",
      "注册时间": "2007-10-09",
      "到期时间": "2027-10-09",
      "剩余天数": 365,
      "状态": "clientTransferProhibited",
      "DNS": ["ns1.example.com", "..."]
    }
  }
}
```

**错误：** 域名格式错误 `400`；上游失败 `502`。

---

### ICP 备案查询

```
GET /api/domain/icp?domain=baidu.com&timeout=10
```

查询域名 ICP 备案信息（备案号、主体单位、性质、更新时间），最多返回 5 条。

**查询参数：** 同 WHOIS。

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "domain": "baidu.com",
    "available": true,
    "records": [
      {"license": "京ICP证030173号", "unit": "北京百度网讯科技有限公司", "nature": "企业", "updated": "2024-01-01"}
    ]
  }
}
```

---

### 域名综合信息

```
GET /api/domain/info?domain=github.com
```

ICP + WHOIS 一次返回，两个数据源互不影响，各自带 `available` / `error`。

---

## 动态自定义接口

后台创建的自定义接口通过以下路径访问，支持 GET / POST / PUT / PATCH / DELETE。

```
ANY /api/{slug}
ANY /api/custom/{slug}
```

响应模板支持 `{{变量}}` 语法，可用变量：

| 变量 | 说明 |
|------|------|
| `{{slug}}` | 接口标识 |
| `{{method}}` | 请求方法 |
| `{{path}}` | 请求路径 |
| `{{query.name}}` | 查询参数 |
| `{{headers.User-Agent}}` | 请求头 |
| `{{body}}` | 请求体原文 |
| `{{json.field}}` | JSON 请求体字段 |
| `{{client.host}}` | 客户端 IP |
| `{{now.iso}}` / `{{now.timestamp}}` | 当前时间 |

**响应类型：** json / text / html，由后台配置决定。

**错误：** 接口不存在 `404`；已停用 `403`；方法不匹配 `405`；JSON 模板配置错误 `500`。

---

## 系统服务

### API 版本信息

```
GET /api/version
```

**响应示例：**
```json
{"code": 200, "msg": "success", "data": {"current": "v1", "legacy_prefix": "/api", "versioned_prefix": "/api/v1", "compatibility": "旧路径继续可用，新项目建议逐步使用 /api/v1"}}
```

---

### 健康检查

```
GET /health
```

**响应示例：**
```json
{"status": "ok", "app": "绿夜API", "environment": "development", "database": "ok", "apis": 30, "api_keys": 4}
```

---

## 门户与页面

| 路径 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页（接口门户） |
| `/test` | GET | 接口测试台（浏览器内直接调参试调） |
| `/register` | GET | 自助注册页 |
| `/register/key` | POST | 自助生成 Api-Key，参数 `name` |
| `/portal/apis` | GET | 接口目录数据（含分类、统计、调用次数） |
| `/portal/apis/{name}` | GET | 单个接口详情数据 |
| `/portal/site` | GET | 站点配置信息 |
| `/doc/{name}.html` | GET | 单个接口文档页 |
| `/health` | GET | 健康检查 |

---

## 后台管理

> 后台路径默认为 `/manage-api`，可通过 `admin_public_path` 配置修改。所有接口需 `Admin-Token` 请求头或 `admin_token` Cookie（登录后自动设置）。

### 认证

| 路径 | 方法 | 说明 |
|------|------|------|
| `/manage-api/login` | POST | 登录，Body `{"token": "xxx"}`，失败有 IP 限流（默认 5 次/300秒） |
| `/manage-api/logout` | POST | 登出，清除 Cookie |
| `/manage-api/session` | GET | 当前会话信息 |

### 接口管理

| 路径 | 方法 | 说明 |
|------|------|------|
| `/manage-api/apis` | GET | 接口列表 |
| `/manage-api/apis` | POST | 创建自定义接口 |
| `/manage-api/apis/{name}` | PATCH | 更新接口（内置接口的 path/method/response 不可改） |
| `/manage-api/apis/{name}` | DELETE | 删除接口（仅自定义） |
| `/manage-api/categories` | GET | 分类统计 |
| `/manage-api/route-check` | GET | 路由巡检（标记数据库中已失效的幽灵接口） |

### Key 管理

| 路径 | 方法 | 说明 |
|------|------|------|
| `/manage-api/keys` | GET | Key 列表（含额度、今日用量） |
| `/manage-api/keys` | POST | 创建 Key，参数 `key` / `name` / `quota_per_day` |
| `/manage-api/keys/{key}` | PATCH | 更新 Key，参数 `enabled` / `quota_per_day` |
| `/manage-api/keys/{key}` | DELETE | 删除 Key |

### 统计与日志

| 路径 | 方法 | 说明 |
|------|------|------|
| `/manage-api/stats` | GET | 调用统计（按接口、按 Key、最近访问） |
| `/manage-api/access-logs` | GET | 访问日志，参数 `limit`(1-500) / `status_min` |
| `/manage-api/access-logs.csv` | GET | 日志 CSV 导出（含公式注入防护），参数 `limit`(1-10000) |
| `/manage-api/douyin-health` | GET | 抖音解析健康状态（连续失败次数、告警阈值） |

### 站点与备份

| 路径 | 方法 | 说明 |
|------|------|------|
| `/manage-api/site-settings` | GET | 站点配置 |
| `/manage-api/site-settings` | PATCH | 更新站点配置（site_name / logo_text / hero_title / hero_subtitle） |
| `/manage-api/backup/database` | GET | 下载 SQLite 数据库备份 |

---

## 通用说明

### 统一响应格式

成功：
```json
{"code": 200, "msg": "success", "data": {...}}
```

失败：
```json
{"code": 400, "msg": "错误描述", "detail": "错误描述", "request_id": "xxx"}
```

### 限流

- 默认单 IP 每分钟 120 次（`/api/*` 和 `/register/key`）
- 超过返回 `429`，响应头含 `Retry-After: 60`
- 可通过 `rate_limit_per_minute` 配置，设为 0 关闭限流

### 鉴权

- 公开接口默认免 Api-Key
- 传了 Api-Key（`Api-Key` 或 `X-API-Key` 头）会校验有效性并计入额度
- `require_api_key: true` 时所有接口必须传 Key
- 后台接口必须传 `Admin-Token` 头或登录 Cookie

### 安全

- 后台登录失败有 IP 级限流（默认 5 次/300秒）
- 生产环境（`environment=production`）弱口令直接拒绝启动
- 监听非回环地址时弱口令打印告警
- 所有响应带安全头（X-Content-Type-Options、X-Frame-Options、Referrer-Policy、Permissions-Policy）
- 生产环境额外带 HSTS
- 日志和统计中 Api-Key 自动脱敏
- CSV 导出防公式注入

### 版本化

所有 `/api/*` 接口同时支持 `/api/v1/*` 路径，例如：
- `/api/tool/hash` ≡ `/api/v1/tool/hash`
- `/api/ip` ≡ `/api/v1/ip`

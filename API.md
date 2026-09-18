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

抖音去水印解析，支持图文、短视频和实况解析，支持分享短链接。可通过 `enable_douyin` 配置关闭。

**查询参数 / POST Body（JSON）：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| url / text | string | 是 | — | 抖音分享链接或包含链接的完整分享文本 |
| timeout | float | 否 | 6.0 | 服务端请求超时，2-20 秒 |
| debug | bool | 否 | false | 解析失败时返回页面诊断信息 |
| probe | bool | 否 | false | 只探测短链跳转和页面摘要，不强制解析视频数据 |

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
    "music": {"title": "背景音乐", "url": "https://..."},
    "images": []
  }
}
```

**错误：** 缺少 url 返回 `400`；解析失败返回 `400`（debug/probe 模式附带诊断信息）。

---

## 爬虫聚合

> 以下接口返回本地种子数据（`sample: true`），结构参考真实爬虫接口，非实时数据源。

### 新闻分类

```
GET /api/news/categories
```

返回新闻分类列表。

**响应示例：**
```json
{"code": 200, "msg": "success", "data": [{"type": 0, "name": "头条"}, {"type": 1, "name": "军事"}, "..."]}
```

---

### 新闻列表

```
GET /api/news/list?type=0&page=1&size=10
```

按分类分页返回新闻列表。

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| type | int | 否 | 0 | 分类下标，0-7 |
| page | int | 否 | 1 | 页码，>=1 |
| size | int | 否 | 10 | 每页条数，1-50 |

**响应示例：**
```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "page": 1, "size": 5, "total": 4,
    "items": [{"postid": "N20260521001-0-1", "title": "...", "source": "科技日报", "digest": "...", "ptime": "2026-09-18 09:01:00"}],
    "sample": true
  }
}
```

---

### 新闻详情

```
GET /api/news/detail?postid=N20260521001-0-1
```

按 postid 返回新闻详情。未知 postid 返回 `404`。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| postid | string | 是 | 新闻 ID，>=3 字符 |

---

### 视频列表

```
GET /api/video/list?type=全部&page=1&size=10
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| type | string | 否 | 全部 | 视频类型筛选 |
| page | int | 否 | 1 | 页码 |
| size | int | 否 | 10 | 每页条数，1-50 |

---

### 视频详情

```
GET /api/video/detail?vid=V10001
```

未知 vid 返回 `404`。

---

### 图片相册

```
GET /api/picture/cosplay?page=1&size=10
```

**查询参数：**

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| page | int | 否 | 1 | 页码 |
| size | int | 否 | 10 | 每页条数，1-30 |

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

# 可二开开源 API 项目（补充方向）

> 排除你们已有的：抖音、手机号、whois/ICP、IP、一言、随机头像、短链、B站封面、Bing壁纸、二维码、工具类（时间戳/hash/base64/uuid）、新闻/视频/COS/历史上今天/成语/唐诗爬虫、占卜
> 筛选标准：有源码、可自部署或当库用、能集成进 FastAPI

---

## 一、多平台热榜聚合（你们只有 news 爬虫，没有热榜）

| 项目 | 语言 | 形式 | 支持平台 | 集成方式 |
|------|------|------|---------|---------|
| [seesea-core](https://pypi.org/project/seesea-core/) | Python | **pip 库** | 知乎/微博/GitHub Trending/掘金/B站/贴吧/豆瓣/喜马拉雅/少数派/IT之家/36氪/虎嗅等 | `pip install seesea-core`，直接当库调用，支持并发 |
| [Tuzkiss/DailyHotApi-X](https://github.com/Tuzkiss/DailyHotApi-X) | TypeScript | REST API | B站/AcFun/微博/知乎/知乎日报/百度/抖音/头条/36氪/少数派/IT之家/掘金/CSDN/豆瓣/百度贴吧/喜马拉雅/澎湃/悟空日报/番茄小说/快手/贴吧/腾讯新闻/网易新闻/LOL/原神/王者荣耀/Steam/Epic/机核/V2EX/水木社区/无忧精英/中文网/凤凰网/新浪新闻/搜狐/虎扑/微信读书/得到/华尔街见闻/财新/第一财经/同花顺/东方财富/雪球/集思录/什么值得买/豆瓣电影/豆瓣小组/豆瓣音乐/豆瓣同城/豆瓣小组/豆瓣时间/豆瓣阅读/豆瓣豆品/豆瓣时间/豆瓣小组 | Vercel/Docker 部署，调 REST |
| [sansan0/TrendRadar](https://github.com/sansan0/TrendRadar) | Python | 独立服务 | 微博/知乎/抖音/百度/头条/华尔街见闻/B站等 11 平台 | 30 秒部署，有智能推送 |

> **推荐**：`seesea-core`，Python 库直接集成，不用额外部署服务。一个接口返回所有平台热榜。

---

## 二、天气（你们没有）

| 项目 | 形式 | 特点 | 集成方式 |
|------|------|------|---------|
| [Open-Meteo](https://github.com/open-meteo/open-meteo) | **开源免 key 在线 API** + 可自部署 | 聚合 NOAA/DWD/ECMWF 等多国气象数据，CC BY 4.0，无需注册，有官方 Python 库 `open-meteo` | `pip install open-meteo`，异步客户端，直接调在线 API；也可 Docker 自部署（需下载气象数据） |

> **推荐**：直接用 Open-Meteo 在线 API，免 key 免部署，`pip install open-meteo` 就行。自部署需要 GB 级气象数据，不划算。

---

## 三、验证码生成（你们没有）

| 项目 | 语言 | 形式 | 特点 | 集成方式 |
|------|------|------|------|---------|
| [captchakit](https://pypi.org/project/captchakit/) | Python | **pip 库** | 异步优先，零依赖（只需 Pillow），**内置 FastAPI 适配器**，4 种主题（经典/暗色/粉彩/高对比度WCAG），SVG + 音频渲染，Redis/PG 存储，限流，Prometheus 指标 | `pip install captchakit`，FastAPI 直接集成 |
| [easy-captcha-python](https://pypi.org/project/easy-captcha-python/) | Python | pip 库 | 支持 GIF 动图、中文、算术、数字字母，Java EasyCaptcha 的 Python 版 | `pip install easy-captcha-python` |
| [tollbooth](https://pypi.org/project/tollbooth/) | Python | pip 库 | **滑动验证码** + 圆点验证码，WSGI 中间件，token TTL | `pip install tollbooth[image]` |

> **推荐**：`captchakit`，专门适配 FastAPI，生产级，带限流和存储。

---

## 四、万年历 / 老黄历 / 节假日（你们没有）

| 项目 | 语言 | 形式 | 特点 | 集成方式 |
|------|------|------|------|---------|
| [lunar](https://github.com/6tail/lunar-python) | Python | **pip 库，零依赖** | 公历/农历/老黄历/佛历/道历，支持星座/干支/生肖/节气/彭祖百忌/吉神方位/冲煞/纳音/星宿/八字/五行/建除十二值/黄道黑道等，**纯算法离线** | `pip install lunar`，纯算法，无网络依赖 |
| [chinesecalendar](https://pypi.org/project/chinesecalendar/) | Python | pip 库 | 判断工作日/节假日/调休，支持 2004-2026 年 | `pip install chinesecalendar` |
| [fcalendar](https://pypi.org/project/fcalendar/) | Python | pip 库 | 农历 + 节假日 + CLI，中英文 | `pip install fcalendar` |

> **推荐**：`lunar`，功能最全，零依赖纯算法，跟你们的占卜模块很搭，可以做老黄历/八字/宜忌接口。

---

## 五、随机图片 / 二次元壁纸（你们有随机头像和Bing壁纸，但没有通用随机图）

| 项目 | 语言 | 形式 | 特点 | 集成方式 |
|------|------|------|------|---------|
| [Random Mage (new-pixiv-api)](https://github.com/) | Python | 自托管服务 | **Pixiv 随机图片**，按标签/热度/分辨率/R18/AI/作品类型筛选，有管理后台 Web UI + Worker，原图存本地数据库 | Docker 部署，调 REST API |
| [CloudImageAPI](https://github.com/) | Python(Flask) | 自托管服务 | 云存储（OSS/图床）图片随机，按终端类型（desktop/mobile）返回不同尺寸，有增删改查管理接口 | Docker 部署 |
| [dreamfishyx/random_image_api](https://github.com/dreamfishyx/random_image_api) | Python | 自托管服务 | 轻量随机图片 API，Docker 一键部署 | Docker 部署 |

> **注意**：随机图片需要自己准备图源或爬取，存储成本高。如果只是要个接口，可以直接用 `lunar` + 本地图片目录写个简单路由，不需要引入复杂项目。

---

## 六、综合 API 集合（一次挖多个）

| 项目 | 语言 | 包含内容 | 形式 |
|------|------|---------|------|
| [60s API](https://github.com/) | 多语言 | 每天 60 秒看世界 + 微博/知乎/B站/抖音/小红书热搜 + 金价 + 油价 + 天气 + 翻译 + 壁纸 + 二维码 + 猫眼票房 + Epic 游戏 | Docker / Cloudflare Workers / Deno / Bun |

> 60s API 里有不少你们没有的：60秒看世界、金价、油价、猫眼票房、Epic 免费游戏。可以参考其实现逐个移植。

---

## 七、快递查询（不推荐）

快递查询开源免 key 的几乎没有，主流方案（快递100/快递鸟/菜鸟）都需要注册 key。如果要做，只能写爬虫，但各快递公司反爬严格，稳定性差。**不建议花时间在这上面。**

---

## 集成优先级建议

| 优先级 | 项目 | 理由 | 工作量 |
|--------|------|------|--------|
| ⭐⭐⭐ | `seesea-core` 热榜 | Python 库，pip 装完直接用，一个接口覆盖 10+ 平台热榜 | 半天 |
| ⭐⭐⭐ | `lunar` 万年历 | 零依赖纯算法，跟你们占卜模块搭，可做老黄历/八字/宜忌/节气 | 半天 |
| ⭐⭐⭐ | Open-Meteo 天气 | 免 key 在线 API，pip 装客户端，你们没有天气接口 | 2小时 |
| ⭐⭐ | `captchakit` 验证码 | FastAPI 原生适配，生产级，可用于注册/登录防护 | 1天 |
| ⭐⭐ | `chinesecalendar` 节假日 | pip 库，判断工作日/节假日/调休 | 2小时 |
| ⭐ | 60s API 参考 | 移植金价/油价/60秒看世界等小众接口 | 按需 |
| ⭐ | Random Mage 随机图 | 需要图源和存储，成本高 | 1周+ |
| ❌ | 快递查询 | 无开源免 key 方案，爬虫不稳定 | 不建议 |

---

## 最值得立刻加的 3 个

1. **多平台热榜**（已实现，自建 `apis/hot/`）— 微博/百度/GitHub/B站，5 分钟缓存，GitHub 走代理
2. **万年历/老黄历**（`lunar`）— 零依赖纯算法，跟你们占卜模块完美搭配，可扩展出宜忌/八字/节气接口
3. **汇率**（Frankfurter）— 开源免 key，ECB 数据，可自托管，你们目前没有汇率接口

---

## 第二轮补充发现

### 综合 API 集合（可移植单个接口）

| 项目 | 语言 | 包含内容 | 形式 | 备注 |
|------|------|---------|------|------|
| [vikiboss/60s](https://github.com/vikiboss/60s) | TypeScript | 60秒看世界、AI新闻、汇率换算、壁纸、历史今天、Epic免费游戏、热搜榜（小红书/B站/抖音/知乎/微博/头条/懂车帝/网易云/猫眼）、实时天气、查歌词、翻译、百度百科、段子、一言、摸鱼日报、发病文学、金价、油价 | Docker / Deno / Bun / Cloudflare Workers | 最有参考价值，每个子接口都有独立实现，可逐个移植 |

### 汇率

| 项目 | 形式 | 特点 | 集成方式 |
|------|------|------|---------|
| [Frankfurter](https://github.com/hakanensari/frankfurter) | 开源 API + 可自托管 | 基于欧洲央行每日参考汇率，**免 key 无限次**，30+ 货币，支持历史汇率 | 直接调在线 API `https://api.frankfurter.app`，或 Docker 自托管 |
| forex-python | pip 库 | 基于 ratesapi.io，汇率转换 + 比特币价格 | `pip install forex-python` |

### 金融数据

| 项目 | 形式 | 特点 | 集成方式 |
|------|------|------|---------|
| [akshare](https://github.com/akfamily/akshare) | **pip 库，MIT** | A股/港股/美股实时+历史行情、汇率、指数、加密货币、K线，数据来源公开 | `pip install akshare`，直接当库用 |
| [aktools](https://github.com/akfamily/aktools) | 独立 API 服务 | 基于 akshare 的 REST API，Docker 一键部署 | `docker run -d --name aktools -p 8080:8080 akfamily/aktools` |

### 金价 / 油价（免 key 公开接口）

| 数据 | 接口 | 说明 |
|------|------|------|
| 黄金/白银/原油 | `https://qt.gtimg.cn/q=hf_GC,hf_SI,hf_CL` | 腾讯财经，免 key，浏览器端可用，支持批量 |
| 黄金 | `https://hq.sinajs.cn/list=hf_GC` | 新浪财经，需 Referer 头，仅服务端可用 |
| 国内油价 | 参考 60s API 实现 | 数据来源 huangjinjiage.cn，按省份爬取 |

### 段子 / 笑话

| 项目 | 形式 | 特点 |
|------|------|------|
| [ckx-jokes](https://pypi.org/project/ckx-jokes/) | Flask REST API | 多分类、多语言、单条/批量/无限流，可自托管 |

### 更新后的优先级

| 优先级 | 项目 | 理由 | 工作量 |
|--------|------|------|--------|
| ⭐⭐⭐ | 热榜（已完成） | 自建模块，4 平台实测通过 | 已完成 |
| ⭐⭐⭐ | `lunar` 万年历 | 零依赖纯算法，跟占卜模块搭 | 半天 |
| ⭐⭐⭐ | Frankfurter 汇率 | 开源免 key，可自托管，无汇率接口 | 2小时 |
| ⭐⭐ | Open-Meteo 天气 | 免 key 在线 API | 2小时 |
| ⭐⭐ | `akshare` 金融数据 | MIT，pip 库，A股/汇率/指数 | 半天 |
| ⭐⭐ | `captchakit` 验证码 | FastAPI 原生适配 | 1天 |
| ⭐⭐ | `chinesecalendar` 节假日 | pip 库，工作日/节假日判断 | 2小时 |
| ⭐ | 60s API 移植（金价/油价/60秒） | 参考其爬虫实现 | 按需 |
| ⭐ | ckx-jokes 段子 | Flask，可移植逻辑 | 半天 |
| ⭐ | Random Mage 随机图 | 需图源和存储，成本高 | 1周+ |
| ❌ | 快递查询 | 无开源免 key 方案 | 不建议 |
| ❌ | seesea-core | 重型 Rust 平台，AGPL 协议，需初始化运行时 | 已否决 |

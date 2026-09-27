# 待办事项

> 来源：2026-09-27 文档与代码审查。已修复项见 git 历史，这里只列尚未处理的。

## 安全（暂缓，项目目前仅本地运行）

- [ ] 轮换测试报告中出现过的 Api-Key，以及 `config.json` / `config.production.json` 中的 admin_token、默认 Key、视频号与小红书 Cookie
- [ ] 默认口令 `admin888` / 默认 Key `test123` 仅限开发使用，上线前必须修改

## 代码

- [ ] 统一响应格式：成功响应的结构仍不统一（如 music 多一个顶层 `total` 字段），错误响应已统一为「HTTP 状态码 + `{code, msg}`」

## 文档

- [ ] 新增/删除接口时同步更新 `API.md`、`CURL_TESTS.md`

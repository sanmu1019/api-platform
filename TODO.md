# 待办事项

> 来源：2026-09-27 文档与代码审查。已修复项见 git 历史，这里只列尚未处理的。

## 凭据（本地已于 2026-09-27 轮换，以下需人工处理）

- [ ] **线上服务器**：本地 `config.production.json` 已换成新的 admin_token 和默认 Key，需同步到服务器并重启；服务器上旧 Key 仍有效，登录后台停用
- [ ] **视频号 / 小红书 Cookie**：`config.json` 里的 `wxsph_cookie`、`xiaohongshu_cookie` 无法在本地轮换。在元宝和小红书网页端退出登录让旧会话失效，再重新登录复制新 Cookie

## 代码质量

- [ ] **成功响应格式不统一**：如 music 多一个顶层 `total` 字段；错误响应已统一为「HTTP 状态码 + `{code, msg}`」

## 文档

- [ ] 新增/删除接口时同步更新 `API.md`、`CURL_TESTS.md`

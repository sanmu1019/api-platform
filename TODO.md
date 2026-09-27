# 待办事项

> 来源：2026-09-27 文档与代码审查。已修复项见 git 历史，这里只列尚未处理的，按优先级排列。

## 1. 同步远程仓库（先做）

- [ ] **本地 `main` 与 `origin/main` 已分叉**：远程有 16 个本地没有的提交，本地有 12 个远程没有的提交（2026-09-27 `git fetch` 结果）。
  1. `git log --oneline HEAD..origin/main` 查看远程多出的提交，确认是谁、改了什么
  2. `git pull --rebase origin main`（或 merge），解决冲突
  3. `python -m pytest -q` 全部通过后再 `git push origin main`
  - 本地分支没有设置 upstream，推送时加 `-u`

## 2. 凭据（本地已于 2026-09-27 轮换，以下需人工处理）

轮换前的配置和数据库备份在 `backup/*.pre-rotate-20260927`（不入库），确认线上正常后可删除。

- [ ] **线上服务器**：
  1. 把本地 `config.production.json` 的 `admin_token`、`default_api_keys` 同步到服务器的 `config.json`
  2. 重启服务（`docker compose up -d` 或 `systemctl restart api-platform`）
  3. 用新 token 登录后台，在「Api-Key 管理」里停用旧的默认 Key 和测试报告里出现过的 `ak_vOy5…`
  4. 通知使用旧 Key 的调用方换新 Key
- [ ] **视频号 Cookie**（`wxsph_cookie`）：在元宝网页端退出登录，使旧会话失效；重新登录后复制新 Cookie 写入 `config.json`
- [ ] **小红书 Cookie**（`xiaohongshu_cookie`）：同上，在小红书网页端退出后重新登录复制

## 3. 可选配置

- [ ] **QQ 音乐播放地址**：需要的话在 `config.json` 填 `qqmusic_cookie`（登录 y.qq.com 后复制整串 Cookie，需含 `uin` 和 `qqmusic_key`）。登录态几天到一个月过期，过期后接口返回的 `note` 会提示；用自己的账号批量取播放地址违反 QQ 音乐用户协议，只建议低频私用。未实测过真实账号，填好后请搜一首歌确认 `play_url` 非空

## 4. 代码质量

- [ ] **成功响应格式不统一**：错误响应已统一为「HTTP 状态码 + `{code, msg}`」，成功响应还有差异，如 music 多一个顶层 `total`、`note` 字段。统一为 `{code, msg, data}`，额外字段放进 `data`，改完同步 `API.md` 和前端测试台

## 5. 本地清理

- [ ] 根目录 `tmp_result.txt`、`tmp_scrape_jokes.py`、`tmp_url.py` 已被忽略，不再需要就删除
- [ ] `PROGRESS.md` 停在 2026-07-02 已过时（被忽略，只在本地），删除或更新

## 6. 长期约定

- [ ] 新增/删除接口时同步更新 `API.md`、`CURL_TESTS.md`，并补测试（参考 `tests/test_modules.py`，上游请求一律 monkeypatch）

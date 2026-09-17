const $ = id => document.getElementById(id);
const ADMIN_BASE = (window.__ADMIN_BASE__ || "/manage-api").replace(/\/$/, "");
let editing = null;
let apiRows = [];

const TXT = {
  ok: "成功",
  loaded: "加载完成",
  loginOk: "会话已刷新",
  saved: "已保存",
  created: "已创建",
  updated: "已更新",
  deleted: "已删除",
  enabled: "启用",
  disabled: "停用",
  builtin: "内置",
  custom: "自定义",
  noData: "暂无数据",
  noMatch: "没有匹配的接口",
  allCategories: "全部分类",
  defaultCategory: "默认分类"
};

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function setStatus(text, ok = true) {
  const el = $("status");
  if (!el) return;
  el.textContent = text;
  el.className = ok ? "hint ok" : "hint danger";
}

function setLoggedOut(message = "已退出") {
  document.body.classList.remove("admin-authed");
  document.body.classList.add("admin-locked");
  clearAdminData();
  setStatus(message, true);
}

function clearAdminData() {
  ["countApis", "countCustom", "countKeys", "countCalls"].forEach(id => {
    if ($(id)) $(id).textContent = "-";
  });
  ["apisTable", "keysTable", "statsBox", "debugApi", "debugResult"].forEach(id => {
    if ($(id)) $(id).innerHTML = "";
  });
  apiRows = [];
}

async function api(path, options = {}) {
  const url = path.startsWith("/admin/") ? ADMIN_BASE + path.slice("/admin".length) : path;
  const res = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers: { ...(options.headers || {}) }
  });
  let data = {};
  try {
    data = await res.json();
  } catch (_) {
    data = { detail: await res.text() };
  }
  if (!res.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data));
  }
  return data;
}

async function login() {
  try {
    const token = $("token")?.value.trim();
    if (token) {
      await api("/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token })
      });
      $("token").value = "";
    } else {
      await api("/admin/session");
    }
    document.body.classList.add("admin-authed");
    document.body.classList.remove("admin-locked");
    setStatus(TXT.loginOk);
    await reloadAll();
  } catch (e) {
    setStatus(e.message, false);
  }
}

function fillSiteForm(data) {
  data = data || {};
  if ($("siteName")) $("siteName").value = data.site_name || "";
  if ($("logoText")) $("logoText").value = data.logo_text || "";
  if ($("heroTitleInput")) $("heroTitleInput").value = data.hero_title || "";
  if ($("heroSubtitleInput")) $("heroSubtitleInput").value = data.hero_subtitle || "";
}

async function loadSiteSettings() {
  const data = await api("/admin/site-settings");
  fillSiteForm(data.data || {});
}

async function saveSiteSettings() {
  try {
    const payload = {
      site_name: $("siteName").value.trim(),
      logo_text: $("logoText").value.trim(),
      hero_title: $("heroTitleInput").value.trim(),
      hero_subtitle: $("heroSubtitleInput").value.trim()
    };
    const data = await api("/admin/site-settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    fillSiteForm(data.data || payload);
    setStatus(TXT.saved);
  } catch (e) {
    setStatus(e.message, false);
  }
}

function defaultBody() {
  return '{"code":200,"msg":"success","data":{"name":"{{query.name}}","time":"{{now.iso}}"}}';
}

function openApiForm(row = null) {
  editing = row;
  const box = $("apiForm");
  box.classList.remove("hidden");
  box.innerHTML = `
    <input id="fName" placeholder="name，例如 hello" value="${row ? escapeHtml(row.name) : ""}" ${row ? "disabled" : ""} oninput="syncPath()">
    <input id="fTitle" placeholder="标题" value="${row ? escapeHtml(row.title) : ""}">
    <input id="fPath" placeholder="路径，例如 /api/hello" value="${row ? escapeHtml(row.path) : "/api/"}">
    <input id="fCategory" placeholder="分类" value="${row ? escapeHtml(row.category || "") : "自定义"}">
    <select id="fMethod">${["GET", "POST", "PUT", "PATCH", "DELETE"].map(m => `<option value="${m}" ${row && row.method === m ? "selected" : ""}>${m}</option>`).join("")}</select>
    <select id="fType">${["json", "text", "html"].map(t => `<option value="${t}" ${row && row.response_type === t ? "selected" : ""}>${t}</option>`).join("")}</select>
    <input id="fStatus" type="number" min="100" max="599" placeholder="HTTP 状态码" value="${row ? (row.status_code || 200) : 200}">
    <input id="fSort" type="number" placeholder="排序" value="${row ? (row.sort_order || 100) : 100}">
    <input id="fDesc" class="full" placeholder="描述" value="${row ? escapeHtml(row.description) : ""}">
    <textarea id="fBody" class="full" rows="8" placeholder="响应内容，支持 {{query.name}}、{{json.xxx}}、{{now.iso}}">${row ? escapeHtml(row.response_body || "") : defaultBody()}</textarea>
    <label class="check"><input id="fEnabled" type="checkbox" ${!row || row.enabled ? "checked" : ""}> 启用</label>
    <div class="full admin-actions"><button class="btn primary" onclick="saveApi()">保存</button><button class="btn ghost" onclick="cancelApiForm()">取消</button></div>`;
}

function syncPath() {
  const name = $("fName")?.value.trim();
  if (name && $("fPath") && $("fPath").value === "/api/") $("fPath").value = `/api/${name}`;
}

function cancelApiForm() {
  $("apiForm").classList.add("hidden");
  $("apiForm").innerHTML = "";
  editing = null;
}

async function saveApi() {
  try {
    const name = editing ? editing.name : $("fName").value.trim();
    // 必须先记下是不是编辑态：cancelApiForm() 会把 editing 置为 null，
    // 之后再读 editing 就恒为 null，导致"更新"也被提示成"已创建"。
    const isEdit = Boolean(editing);
    const payload = new URLSearchParams({
      name,
      title: $("fTitle").value.trim(),
      path: $("fPath").value.trim(),
      category: $("fCategory").value.trim(),
      method: $("fMethod").value,
      response_type: $("fType").value,
      response_body: $("fBody").value,
      status_code: $("fStatus").value || "200",
      description: $("fDesc").value.trim(),
      sort_order: $("fSort").value || "100",
      enabled: $("fEnabled").checked
    });
    const url = isEdit ? `/admin/apis/${encodeURIComponent(editing.name)}?${payload}` : `/admin/apis?${payload}`;
    await api(url, { method: isEdit ? "PATCH" : "POST" });
    cancelApiForm();
    await reloadAll();
    setStatus(isEdit ? TXT.updated : TXT.created);
  } catch (e) {
    setStatus(e.message, false);
  }
}

async function loadApis() {
  const data = await api("/admin/apis");
  apiRows = data.data || [];
  $("countApis").textContent = apiRows.length;
  $("countCustom").textContent = apiRows.filter(x => !x.is_builtin).length;
  renderCategoryFilter();
  renderApisTable();
  renderDebugOptions();
}

function renderCategoryFilter() {
  const select = $("adminCategoryFilter");
  if (!select) return;
  const current = select.value;
  const categories = Array.from(new Set(apiRows.map(x => x.category || TXT.defaultCategory))).sort();
  select.innerHTML = `<option value="">${TXT.allCategories}</option>` + categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
  select.value = current;
}

function filteredApiRows() {
  const q = ($("adminApiSearch")?.value || "").trim().toLowerCase();
  const c = $("adminCategoryFilter")?.value || "";
  return apiRows.filter(x => {
    const text = `${x.name} ${x.title} ${x.path} ${x.description}`.toLowerCase();
    return (!q || text.includes(q)) && (!c || (x.category || TXT.defaultCategory) === c);
  });
}

function clearApiFilter() {
  $("adminApiSearch").value = "";
  $("adminCategoryFilter").value = "";
  renderApisTable();
}

function renderApisTable() {
  const rows = filteredApiRows();
  $("apisTable").innerHTML = `<table class="admin-table"><thead><tr><th>接口</th><th>分类</th><th>方法</th><th>地址</th><th>响应</th><th>状态</th><th>操作</th></tr></thead><tbody>${
    rows.map(x => {
      const callPath = x.is_builtin ? x.path : `/api/${x.name}`;
      const rowJson = escapeHtml(JSON.stringify(x));
      return `<tr>
        <td><div class="title">${escapeHtml(x.title)}</div><div class="muted">${escapeHtml(x.name)} <span class="tag ${x.is_builtin ? "" : "soft"}">${x.is_builtin ? TXT.builtin : TXT.custom}</span></div></td>
        <td>${escapeHtml(x.category || "")}</td>
        <td><code>${escapeHtml(x.method || "GET")}</code></td>
        <td><div><code>${escapeHtml(callPath)}</code></div><div class="muted">文档：<a href="/doc/${encodeURIComponent(x.name)}.html" target="_blank">/doc/${escapeHtml(x.name)}.html</a></div></td>
        <td>${escapeHtml(x.response_type || "json")} / ${x.status_code || 200}</td>
        <td><span class="status ${x.enabled ? "on" : "off"}">${x.enabled ? TXT.enabled : TXT.disabled}</span></td>
        <td class="ops">${x.is_builtin ? "" : `<button class="btn tiny" onclick='editApi(JSON.parse(this.dataset.row))' data-row='${rowJson}'>编辑</button>`}<button class="btn tiny ${x.enabled ? "warn" : "ok"}" onclick="toggleApi('${escapeHtml(x.name)}', ${!x.enabled})">${x.enabled ? TXT.disabled : TXT.enabled}</button>${x.is_builtin ? "" : `<button class="btn tiny danger" onclick="deleteApi('${escapeHtml(x.name)}')">删除</button>`}</td>
      </tr>`;
    }).join("") || `<tr><td colspan="7" class="muted">${TXT.noMatch}</td></tr>`
  }</tbody></table>`;
}

function editApi(row) {
  openApiForm(row);
}

async function toggleApi(name, enabled) {
  try {
    await api(`/admin/apis/${encodeURIComponent(name)}?enabled=${enabled}`, { method: "PATCH" });
    await reloadAll();
    setStatus(TXT.updated);
  } catch (e) {
    setStatus(e.message, false);
  }
}

async function deleteApi(name) {
  try {
    if (!confirm(`删除接口 ${name}？`)) return;
    await api(`/admin/apis/${encodeURIComponent(name)}`, { method: "DELETE" });
    await reloadAll();
    setStatus(TXT.deleted);
  } catch (e) {
    setStatus(e.message, false);
  }
}

async function loadKeys() {
  const data = await api("/admin/keys");
  const rows = data.data || [];
  $("countKeys").textContent = rows.length;
  $("keysTable").innerHTML = `<table class="admin-table"><thead><tr><th>名称</th><th>Key</th><th>今日用量</th><th>状态</th><th>操作</th></tr></thead><tbody>${
    rows.map(x => {
      const quota = Number(x.quota_per_day || 0);
      const used = Number(x.used_today || 0);
      return `<tr><td>${escapeHtml(x.name)}<div class="muted">创建：${escapeHtml(x.created_at || "-")}</div></td><td><code>${escapeHtml(x.key)}</code></td><td>${used} / ${quota > 0 ? quota : "不限"}<div class="muted">日期：${escapeHtml(x.last_used_date || "-")}</div></td><td><span class="status ${x.enabled ? "on" : "off"}">${x.enabled ? TXT.enabled : TXT.disabled}</span></td><td class="ops"><button class="btn tiny ${x.enabled ? "warn" : "ok"}" onclick="toggleKey('${escapeHtml(x.key)}', ${!x.enabled})">${x.enabled ? TXT.disabled : TXT.enabled}</button><button class="btn tiny" onclick="setKeyQuota('${escapeHtml(x.key)}', ${quota})">额度</button><button class="btn tiny danger" onclick="deleteKey('${escapeHtml(x.key)}')">删除</button></td></tr>`;
    }).join("") || `<tr><td colspan="5" class="muted">${TXT.noData}</td></tr>`
  }</tbody></table>`;
}

function generateKey() {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  $("newKey").value = Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function createKey() {
  try {
    const key = $("newKey").value.trim();
    const name = $("newName").value.trim() || "新用户";
    const quota = Number($("newQuota")?.value || 0);
    if (!key) throw new Error("请输入 key");
    await api(`/admin/keys?key=${encodeURIComponent(key)}&name=${encodeURIComponent(name)}&quota_per_day=${encodeURIComponent(quota)}`, { method: "POST" });
    $("newKey").value = "";
    $("newName").value = "";
    if ($("newQuota")) $("newQuota").value = "";
    await loadKeys();
    setStatus(TXT.created);
  } catch (e) {
    setStatus(e.message, false);
  }
}

async function toggleKey(key, enabled) {
  try {
    await api(`/admin/keys/${encodeURIComponent(key)}?enabled=${enabled}`, { method: "PATCH" });
    await loadKeys();
    setStatus(TXT.updated);
  } catch (e) {
    setStatus(e.message, false);
  }
}

async function setKeyQuota(key, current) {
  try {
    const value = prompt("请输入每日额度，0 表示不限", current || 0);
    if (value === null) return;
    const quota = Number(value);
    if (!Number.isInteger(quota) || quota < 0) throw new Error("额度必须是大于等于 0 的整数");
    await api(`/admin/keys/${encodeURIComponent(key)}?quota_per_day=${quota}`, { method: "PATCH" });
    await loadKeys();
    setStatus(TXT.updated);
  } catch (e) {
    setStatus(e.message, false);
  }
}

async function deleteKey(key) {
  try {
    if (!confirm(`删除 ${key}？`)) return;
    await api(`/admin/keys/${encodeURIComponent(key)}`, { method: "DELETE" });
    await loadKeys();
    setStatus(TXT.deleted);
  } catch (e) {
    setStatus(e.message, false);
  }
}

async function loadStats() {
  const data = await api("/admin/stats");
  const s = data.data || {};
  $("countCalls").textContent = s.total || 0;
  $("statsBox").innerHTML = `<div class="admin-split">
    <div class="admin-card"><h3>按接口</h3><ul>${(s.by_api || []).map(x => `<li>${escapeHtml(x.api_name)}：${x.count}</li>`).join("") || `<li class="muted">${TXT.noData}</li>`}</ul></div>
    <div class="admin-card"><h3>按 Key</h3><ul>${(s.by_key || []).map(x => `<li>${escapeHtml(x.api_key)}：${x.count}</li>`).join("") || `<li class="muted">${TXT.noData}</li>`}</ul></div>
    <div class="admin-card"><h3>访问日志</h3><div class="muted">总访问：${s.access_total || 0}，错误：${s.error_total || 0}</div><ul>${(s.recent_access || []).map(x => `<li><code>${escapeHtml(x.method)}</code> ${escapeHtml(x.path)} / ${x.status_code} / ${x.duration_ms}ms</li>`).join("") || `<li class="muted">${TXT.noData}</li>`}</ul></div>
  </div>`;
}

function renderDebugOptions() {
  if (!$("debugApi")) return;
  $("debugApi").innerHTML = apiRows.filter(x => x.enabled).map(x => {
    const path = x.is_builtin ? x.path : `/api/${x.name}`;
    return `<option value="${escapeHtml(x.name)}" data-path="${escapeHtml(path)}" data-method="${escapeHtml(x.method || "GET")}">${escapeHtml(x.title)} - ${escapeHtml(path)}</option>`;
  }).join("");
  fillDebugPath();
}

function fillDebugPath() {
  const select = $("debugApi");
  const option = select.options[select.selectedIndex];
  if (!option) return;
  $("debugPath").value = option.dataset.path || "";
  $("debugMethod").value = option.dataset.method || "GET";
}

async function debugRequest() {
  try {
    const path = $("debugPath").value.trim();
    if (!path) throw new Error("请输入请求路径");
    const method = $("debugMethod").value;
    const headers = {};
    const apiKey = $("debugKey")?.value.trim();
    if (apiKey) headers["Api-Key"] = apiKey;
    const options = { method, headers };
    const body = $("debugBody").value.trim();
    if (body && method !== "GET") {
      headers["Content-Type"] = "application/json";
      options.body = body;
    }
    const started = performance.now();
    const res = await fetch(path, options);
    const text = await res.text();
    let pretty = text;
    try {
      pretty = JSON.stringify(JSON.parse(text), null, 2);
    } catch (_) {}
    $("debugResult").textContent = `HTTP ${res.status} ${res.statusText}\n耗时：${Math.round(performance.now() - started)}ms\n\n${pretty}`;
  } catch (e) {
    $("debugResult").textContent = e.message;
  }
}

function downloadAccessLogs() {
  window.open(`${ADMIN_BASE}/access-logs.csv?limit=1000`, "_blank");
}

function downloadDatabase() {
  window.open(`${ADMIN_BASE}/backup/database`, "_blank");
}

async function reloadAll() {
  try {
    await Promise.all([loadSiteSettings(), loadApis(), loadKeys(), loadStats()]);
    setStatus(TXT.loaded);
  } catch (e) {
    setStatus(e.message, false);
  }
}

async function bootstrapAdmin() {
  try {
    await api("/admin/session");
    document.body.classList.add("admin-authed");
    document.body.classList.remove("admin-locked");
    await reloadAll();
  } catch (e) {
    setLoggedOut("请输入 Admin-Token 登录");
  }
}

bootstrapAdmin();

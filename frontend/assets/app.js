const $ = id => document.getElementById(id);
let allApis = [];
let categories = [];
let currentCategoryId = "0";
let currentStatusFilter = "all";

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function formatNumber(num) {
  const n = parseInt(num || 0, 10);
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "k";
  return String(n);
}

function normalizeApi(row) {
  const state = row.enabled ? "on" : "maintain";
  return {
    ...row,
    state,
    uri: `/doc/${encodeURIComponent(row.name)}.html`,
    category_id: row.category || "默认分类",
    iconText: (row.title || row.name || "API").slice(0, 1).toUpperCase(),
    pv: row.calls || 0,
    tdpv: Math.floor((row.calls || 0) / 8),
  };
}

function updateHomeStats(summary) {
  $("home-api-count").textContent = formatNumber(summary.total_apis ?? allApis.length);
  $("home-today-count").textContent = formatNumber(summary.today_calls ?? 0);
  $("home-total-count").textContent = formatNumber(summary.total_calls ?? 0);
}

function renderCategoryDropdown() {
  const select = $("category-filter");
  select.innerHTML = '<option value="0">全部分类</option>' +
    categories.map(c => `<option value="${escapeHtml(c.name)}">${escapeHtml(c.name)} (${c.count || 0})</option>`).join("");
}

function renderApiList(list) {
  const container = $("api-list-container");
  $("loading-spinner").style.display = "none";
  $("visible-count").textContent = list.length;
  $("total-count").textContent = allApis.length;
  if (!list.length) {
    container.innerHTML = "";
    $("no-result").hidden = false;
    return;
  }
  $("no-result").hidden = true;
  container.innerHTML = list.map(api => {
    const statusBadge = api.state === "on"
      ? '<span class="bp-mini-badge success">正常</span>'
      : '<span class="bp-mini-badge warn">维护</span>';
    return `<article class="bp-card" data-state="${api.state}" data-category="${escapeHtml(api.category_id)}">
      <a class="bp-card-link" href="${escapeHtml(api.uri)}">
        <div class="bp-card-top">
          <div class="bp-card-icon">${escapeHtml(api.iconText)}</div>
          <div class="bp-card-title"><h3>${escapeHtml(api.title || api.name)}</h3><div>${statusBadge}<span class="bp-mini-badge free">免费</span></div></div>
        </div>
        <p>${escapeHtml(api.description || "暂无描述")}</p>
        <div class="bp-card-foot">
          <span title="累计调用">${formatNumber(api.pv)} 调用</span>
          <span title="今日调用">${formatNumber(api.tdpv)} 今日</span>
          <code>${escapeHtml(api.path)}</code>
        </div>
      </a>
    </article>`;
  }).join("");
}

function applyFilters() {
  const keyword = ($("apiSearch")?.value || $("api-search")?.value || "").trim().toLowerCase();
  let filtered = allApis;
  if (currentCategoryId !== "0") filtered = filtered.filter(api => api.category_id === currentCategoryId);
  if (currentStatusFilter !== "all") filtered = filtered.filter(api => api.state === currentStatusFilter);
  if (keyword) {
    filtered = filtered.filter(api =>
      `${api.name} ${api.title} ${api.description} ${api.path} ${api.category}`.toLowerCase().includes(keyword)
    );
  }
  renderApiList(filtered);
}

function performSearch() { applyFilters(); }
function filterApi(type) { currentStatusFilter = type || "all"; applyFilters(); }
function filterByCategory(categoryId) { currentCategoryId = categoryId || "0"; applyFilters(); }

function applySiteSettings(site) {
  const name = site?.site_name || "绿夜API";
  const heroTitle = site?.hero_title || "绿夜API · 免费公益接口平台";
  const heroSubtitle = site?.hero_subtitle || "提供短视频去水印解析、开发者工具、内容聚合、图片服务等接口，支持在线搜索、分类筛选和文档调试。";
  document.title = name;
  document.querySelectorAll("[data-site-name]").forEach(el => el.textContent = name);
  $("heroTitle").textContent = heroTitle;
  $("heroSubtitle").textContent = heroSubtitle;
}

async function loadHomeApiBundle() {
  const res = await fetch("/portal/apis");
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail || "加载接口失败");
  const data = body.data || {};
  applySiteSettings(data.site || {});
  categories = data.categories || [];
  allApis = (data.apis || []).map(normalizeApi);
  renderCategoryDropdown();
  updateHomeStats(data.summary || {});
  applyFilters();
}

function toggleDarkMode() {
  document.body.classList.toggle("theme-dark");
  localStorage.setItem("darkMode", document.body.classList.contains("theme-dark"));
}

function toggleSidebar() {
  document.body.classList.toggle("sidebar-open");
}

async function loadFooterPhrase() {
  try {
    const res = await fetch("/api/yiyan");
    return await res.json();
  } catch (_) {
    return null;
  }
}

if (localStorage.getItem("darkMode") === "true") document.body.classList.add("theme-dark");
$("apiSearch")?.addEventListener("input", () => {
  clearTimeout(window.__searchTimer);
  window.__searchTimer = setTimeout(applyFilters, 180);
});

loadHomeApiBundle().catch(err => {
  $("loading-spinner").textContent = `加载失败：${err.message}`;
});

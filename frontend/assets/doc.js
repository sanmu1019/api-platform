const root = document.getElementById("docRoot");
const rawName = location.pathname.split("/").pop().replace(/\.html$/, "");
const name = rawName === "douyin" || rawName === "doc-douyin" ? "douyin_parse" : rawName;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const T = {
  detail: "接口详情",
  params: "请求参数",
  code: "示例代码",
  response: "返回示例",
  debug: "在线调试",
  basic: "基本信息",
  apiUrl: "接口地址",
  method: "请求方式",
  format: "返回格式",
  status: "接口状态",
  normal: "正常运行",
  maintain: "维护中",
  copy: "复制",
  send: "发送请求",
  loading: "请求中...",
  result: "响应结果",
  clickSend: "点击左侧发送请求查看结果",
  speed: "测速中...",
  waitDebug: "待调试",
  notFound: "文档不存在",
  loadFail: "加载失败",
  requestExample: "请求示例",
  paramName: "参数名",
  required: "必填",
  type: "类型",
  desc: "说明",
  example: "示例值",
  yes: "是",
  no: "否",
  errorCode: "错误码参考"
};

/* 取本地当天的 MM-DD。
   history/today 的 date 参数示例值必须是"今天" —— 写死成某个固定日期
   （原来写的是 05-21）会让「在线调试」默认演示一个过去的日期，跟接口名
   "today" 自相矛盾：9 月点开调试却看到 5 月 21 日的事件。 */
function todayMMDD() {
  const d = new Date();
  return String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
}

const PARAM_SPECS = {
  word: {
    displayPath: "/api/word/random",
    params: [],
    response: { code: 200, msg: "success", data: { word: "山高路远，行则将至。" } }
  },
  yiyan: {
    displayPath: "/api/yiyan",
    params: [],
    response: { code: 200, msg: "success", data: { text: "先完成，再完美。" } }
  },
  phone: {
    params: [{ name: "phone", required: T.yes, type: "path", desc: "11 位中国大陆手机号", example: "13800138000", in: "path" }]
  },
  avatar_random: {
    exampleQuery: "seed=test-user&style=adventurer",
    params: [
      { name: "seed", required: T.no, type: "string", desc: "头像种子，同一 seed 可生成稳定头像", example: "test-user" },
      { name: "style", required: T.no, type: "string", desc: "DiceBear 风格名称", example: "adventurer" }
    ]
  },
  short_hash: {
    exampleQuery: "url=https%3A%2F%2Fexample.com",
    getTextToQuery: value => `url=${encodeURIComponent(value)}`,
    params: [{ name: "url", required: T.yes, type: "string", desc: "需要生成短标识的 URL", example: "https://example.com" }]
  },
  bilibili_cover: {
    exampleQuery: "bvid=BV1xx411c7mD",
    params: [{ name: "bvid", required: T.yes, type: "string", desc: "B站视频 BV 号", example: "BV1xx411c7mD" }]
  },
  bing_daily: {
    params: [],
    response: { code: 200, msg: "success", data: { title: "Bing Daily Image", url: "https://www.bing.com/...", date: "20260702", source: "bing" } }
  },
  tool_timestamp: {
    exampleQuery: "value=1719900000",
    params: [{ name: "value", required: T.no, type: "number", desc: "Unix 时间戳，默认当前时间", example: "1719900000" }]
  },
  tool_hash: {
    exampleQuery: "text=abc&algorithm=sha256",
    getTextToQuery: value => `text=${encodeURIComponent(value)}`,
    params: [
      { name: "text", required: T.yes, type: "string", desc: "待计算哈希的文本", example: "abc" },
      { name: "algorithm", required: T.no, type: "string", desc: "md5/sha1/sha256/sha512", example: "sha256" }
    ]
  },
  tool_base64: {
    exampleQuery: "text=abc&mode=encode",
    getTextToQuery: value => `text=${encodeURIComponent(value)}`,
    params: [
      { name: "text", required: T.yes, type: "string", desc: "待编码或解码的文本", example: "abc" },
      { name: "mode", required: T.no, type: "string", desc: "encode 或 decode", example: "encode" }
    ]
  },
  tool_uuid: {
    exampleQuery: "count=2",
    params: [{ name: "count", required: T.no, type: "number", desc: "生成数量，1-50", example: "2" }]
  },
  tool_password: {
    exampleQuery: "length=12&symbols=true",
    params: [
      { name: "length", required: T.no, type: "number", desc: "密码长度，6-64", example: "12" },
      { name: "symbols", required: T.no, type: "boolean", desc: "是否包含符号", example: "true" }
    ]
  },
  tool_color: { params: [] },
  tool_nickname: { params: [] },
  image_placeholder: {
    exampleQuery: "width=600&height=400&text=API",
    params: [
      { name: "width", required: T.no, type: "number", desc: "图片宽度", example: "600" },
      { name: "height", required: T.no, type: "number", desc: "图片高度", example: "400" },
      { name: "text", required: T.no, type: "string", desc: "图片文字", example: "API" }
    ]
  },
  image_qrcode: {
    exampleQuery: "text=hello&size=220",
    getTextToQuery: value => `text=${encodeURIComponent(value)}`,
    params: [
      { name: "text", required: T.yes, type: "string", desc: "二维码文本内容", example: "hello" },
      { name: "size", required: T.no, type: "number", desc: "二维码边长，80-800", example: "220" }
    ]
  },
  news_categories: { params: [] },
  news_list: {
    exampleQuery: "type=0&page=1&size=10",
    params: [
      { name: "type", required: T.no, type: "number", desc: "分类编号，0-7", example: "0" },
      { name: "page", required: T.no, type: "number", desc: "页码", example: "1" },
      { name: "size", required: T.no, type: "number", desc: "每页数量", example: "10" }
    ]
  },
  news_detail: {
    exampleQuery: "postid=N20260521001-0-1",
    params: [{ name: "postid", required: T.yes, type: "string", desc: "新闻 ID", example: "N20260521001-0-1" }]
  },
  video_list: {
    exampleQuery: "type=%E5%85%A8%E9%83%A8&page=1&size=10",
    params: [
      { name: "type", required: T.no, type: "string", desc: "视频类型，默认全部", example: "全部" },
      { name: "page", required: T.no, type: "number", desc: "页码", example: "1" },
      { name: "size", required: T.no, type: "number", desc: "每页数量", example: "10" }
    ]
  },
  video_detail: {
    exampleQuery: "vid=V10001",
    params: [{ name: "vid", required: T.yes, type: "string", desc: "视频 ID", example: "V10001" }]
  },
picture_cosplay: {
    exampleQuery: "page=1&size=10",
    params: [
      { name: "page", required: T.no, type: "number", desc: "页码", example: "1" },
      { name: "size", required: T.no, type: "number", desc: "每页数量，1-30", example: "10" }
    ]
  },
  history_today: {
    exampleQuery: `date=${todayMMDD()}`,
    params: [{ name: "date", required: T.no, type: "string", desc: "日期，格式 MM-DD，留空取今天", example: todayMMDD() }]
  },
  douyin_parse: {
    displayPath: "/api/douyin/parse",
    exampleQuery: "url=https%3A%2F%2Fv.douyin.com%2FeEEfBw-3-pQ%2F",
    getTextToQuery: value => `url=${encodeURIComponent(value)}`,
    params: [
      { name: "url", required: T.yes, type: "string", desc: "抖音分享链接，或包含链接的完整分享文本", example: "https://v.douyin.com/eEEfBw-3-pQ/" },
      { name: "debug", required: T.no, type: "boolean", desc: "解析失败时返回诊断信息", example: "false" },
      { name: "probe", required: T.no, type: "boolean", desc: "只探测短链跳转和页面摘要", example: "false" },
      { name: "timeout", required: T.no, type: "number", desc: "服务端请求超时时间，2-20 秒", example: "6" }
    ],
    response: {
      code: 200,
      msg: "success",
      data: {
        aweme_id: "7340000000000000000",
        type: "video",
        title: "示例标题",
        author: { nickname: "作者昵称", avatar: "https://..." },
        cover: "https://...",
        video_url: "https://...",
        images: [],
        music: { title: "背景音乐", url: "https://..." }
      }
    }
  },
  idiom_search: {
    exampleQuery: "keyword=%E7%B2%BE",
    getTextToQuery: value => `keyword=${encodeURIComponent(value)}`,
    params: [{ name: "keyword", required: T.yes, type: "string", desc: "成语词条或拼音（不检索释义）", example: "无懈可击" }]
  },
  poetry_tang: {
    exampleQuery: "keyword=%E6%9D%8E%E7%99%BD&count=1",
    getTextToQuery: value => `keyword=${encodeURIComponent(value)}`,
    params: [
      { name: "keyword", required: T.no, type: "string", desc: "标题、作者或内容关键词", example: "李白" },
      { name: "count", required: T.no, type: "number", desc: "返回数量，1-10", example: "1" }
    ]
  },
};

function appendQuery(path, query) {
  if (!query) return path;
  const clean = query.startsWith("?") ? query.slice(1) : query;
  return path + (path.includes("?") ? "&" : "?") + clean;
}

function setActiveTab(id) {
  document.querySelectorAll(".bp-tab-btn").forEach(btn => btn.classList.toggle("active", btn.dataset.tab === id));
  document.querySelectorAll(".bp-tab-pane").forEach(pane => pane.classList.toggle("active", pane.id === id));
}

function codeExamples(fullUrl, method) {
  return {
    curl: `curl "${fullUrl}"`,
    javascript: `fetch("${fullUrl}", { method: "${method}" })\n  .then(r => r.json())\n  .then(console.log);`,
    python: `import requests\n\nr = requests.${method.toLowerCase()}("${fullUrl}")\nprint(r.json())`,
    php: `<?php\necho file_get_contents("${fullUrl}");\n?>`
  };
}

function applyDocSiteSettings(site) {
  const siteName = site?.site_name || "绿夜API";
  document.querySelectorAll("[data-site-name]").forEach(el => { el.textContent = siteName; });
  return siteName;
}

async function loadDoc() {
  const res = await fetch(`/portal/apis/${encodeURIComponent(name)}`);
  const body = await res.json();
  if (!res.ok) throw new Error(body.detail || T.notFound);
  const row = body.data;
  const siteName = applyDocSiteSettings(body.site || {});
  const spec = PARAM_SPECS[row.name] || {};
  const callPath = spec.displayPath || (row.is_builtin ? row.path : `/api/${row.name}`);
  const examplePath = spec.exampleQuery ? appendQuery(callPath, spec.exampleQuery) : callPath;
  const fullUrl = `${location.origin}${examplePath}`;
  const method = row.method || "GET";
  const responseExample = spec.response || safeJson(row.response_body) || { code: 200, msg: "success", data: {} };
  const params = spec.params || [{ name: "query/body", required: T.no, type: "string/json", desc: "按接口实际说明传入；公开接口默认无需 Api-Key", example: "" }];
  const examples = codeExamples(fullUrl, method);

  document.title = `${row.title} - API文档 - ${siteName}`;
  root.innerHTML = `
    <section class="bp-doc-hero">
      <div class="bp-doc-icon">${esc((row.title || row.name).slice(0, 1))}</div>
      <div class="bp-doc-info">
        <h1>${esc(row.title)}</h1>
        <p>${esc(row.description)}</p>
        <div class="bp-doc-badges">
          <span>${esc(method)}</span><span>${esc((row.response_type || "json").toUpperCase())}</span>
          <span>调用：${row.calls || 0}</span><span id="api-speed-badge">${T.speed}</span>
        </div>
      </div>
      <a class="bp-primary-link" href="${esc(callPath)}" target="_blank">访问接口</a>
    </section>
    <section class="bp-panel">
      <div class="bp-tabs">
        <button class="bp-tab-btn active" data-tab="content-info">${T.detail}</button>
        <button class="bp-tab-btn" data-tab="content-params">${T.params}</button>
        <button class="bp-tab-btn" data-tab="content-code">${T.code}</button>
        <button class="bp-tab-btn" data-tab="content-response">${T.response}</button>
        <button class="bp-tab-btn" data-tab="content-debug">${T.debug}</button>
      </div>
      <div class="bp-tab-pane active" id="content-info">
        <h3>${T.basic}</h3>
        <table class="bp-table"><tbody>
          <tr><th>${T.apiUrl}</th><td><div class="bp-copyline"><input id="api-url-input" value="${esc(location.origin + callPath)}" readonly><button onclick="copyText('api-url-input')">${T.copy}</button></div></td></tr>
          <tr><th>${T.method}</th><td>${esc(method)}</td></tr>
          <tr><th>${T.format}</th><td>${esc((row.response_type || "json").toUpperCase())}</td></tr>
          <tr><th>${T.status}</th><td>${row.enabled ? T.normal : T.maintain}</td></tr>
          <tr><th>${T.requestExample}</th><td><code>${esc(fullUrl)}</code></td></tr>
        </tbody></table>
      </div>
      <div class="bp-tab-pane" id="content-params">
        <h3>请求参数说明</h3>
        <table class="bp-table"><thead><tr><th>${T.paramName}</th><th>${T.required}</th><th>${T.type}</th><th>${T.desc}</th><th>${T.example}</th></tr></thead>
        <tbody>${params.map(p => `<tr><td>${esc(p.name)}</td><td>${esc(p.required)}</td><td>${esc(p.type)}</td><td>${esc(p.desc)}</td><td>${esc(p.example || "")}</td></tr>`).join("")}</tbody></table>
      </div>
      <div class="bp-tab-pane" id="content-code">
        <h3>调用示例</h3>
        <div class="bp-code-grid">${Object.entries(examples).map(([lang, code]) => `<div class="bp-code"><div><b>${lang}</b><button onclick="copyCode(this)">${T.copy}</button></div><pre>${esc(code)}</pre></div>`).join("")}</div>
      </div>
      <div class="bp-tab-pane" id="content-response">
        <h3>返回结果示例</h3>
        <pre class="bp-pre" id="pre-response">${esc(JSON.stringify(responseExample, null, 2))}</pre>
        <h3>${T.errorCode}</h3>
        <table class="bp-table"><tr><th>HTTP ${T.status}</th><th>${T.desc}</th></tr><tr><td>200</td><td>请求成功</td></tr><tr><td>400</td><td>请求参数错误</td></tr><tr><td>403</td><td>接口停用</td></tr><tr><td>404</td><td>接口不存在</td></tr><tr><td>429</td><td>请求过于频繁</td></tr><tr><td>500</td><td>服务端错误</td></tr></table>
      </div>
      <div class="bp-tab-pane" id="content-debug">
        <div class="bp-debug">
          <form onsubmit="return false">
            <h3>调试参数</h3>
            <label>${T.method}<select id="debug-method"><option>${esc(method)}</option><option>GET</option><option>POST</option></select></label>
            <label>${T.apiUrl}<input id="debug-url" value="${esc(callPath)}" readonly></label>
            ${params.filter(p => p.name !== "query/body").map((p, i) => `<label>${esc(p.name)} ${p.required === T.yes ? '<span class="danger">*</span>' : ''}<input class="debug-param-input" data-param-in="${esc(p.in || "query")}" name="${esc(p.name)}" placeholder="${esc(p.desc)}" value="${i === 0 ? esc(p.example || "") : ""}"></label>`).join("")}
            <button class="bp-primary-btn" id="btn-debug-send" type="button" onclick="runDebug()">${T.send}</button>
          </form>
          <div><h3>${T.result} <span id="debug-request-time"></span></h3><pre class="bp-pre" id="debug-result">${T.clickSend}</pre></div>
        </div>
      </div>
    </section>`;

  document.querySelectorAll(".bp-tab-btn").forEach(btn => btn.addEventListener("click", () => setActiveTab(btn.dataset.tab)));
  speedTest(examplePath);
}

function safeJson(value) {
  try {
    return value ? JSON.parse(value) : null;
  } catch (_) {
    return null;
  }
}

function cleanUrlInput(value) {
  const match = String(value || "").match(/https?:\/\/[^\s]+/i);
  return (match ? match[0] : value).trim();
}

function fillPathParams(path, params) {
  let nextPath = path;
  document.querySelectorAll(".debug-param-input[data-param-in='path']").forEach(input => {
    const value = input.value.trim();
    if (value) {
      nextPath = nextPath.replace(`{${input.name}}`, encodeURIComponent(value));
      params.delete(input.name);
    }
  });
  return nextPath;
}

async function runDebug() {
  const btn = document.getElementById("btn-debug-send");
  btn.disabled = true;
  btn.textContent = T.loading;
  let path = document.getElementById("debug-url").value;
  const method = document.getElementById("debug-method").value;
  const params = new URLSearchParams();
  document.querySelectorAll(".debug-param-input").forEach(input => {
    const value = input.name === "url" ? cleanUrlInput(input.value) : input.value.trim();
    if (value) params.set(input.name, value);
  });
  path = fillPathParams(path, params);
  const options = { method };
  if (method === "GET") {
    path = appendQuery(path, params.toString());
  } else {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(Object.fromEntries(params.entries()));
  }
  const started = performance.now();
  try {
    const res = await fetch(path, options);
    const text = await res.text();
    let pretty = text;
    try {
      pretty = JSON.stringify(JSON.parse(text), null, 2);
    } catch (_) {}
    document.getElementById("debug-result").textContent = `HTTP ${res.status} ${res.statusText}\n\n${pretty}`;
    document.getElementById("debug-request-time").textContent = `${Math.round(performance.now() - started)}ms`;
  } catch (e) {
    document.getElementById("debug-result").textContent = e.message;
  } finally {
    btn.disabled = false;
    btn.textContent = T.send;
  }
}

async function speedTest(path) {
  const badge = document.getElementById("api-speed-badge");
  const started = performance.now();
  try {
    await fetch(path, { method: "GET" });
    badge.textContent = `${Math.round(performance.now() - started)}ms`;
  } catch (_) {
    badge.textContent = T.waitDebug;
  }
}

function copyText(id) {
  navigator.clipboard?.writeText(document.getElementById(id).value);
}

function copyCode(btn) {
  navigator.clipboard?.writeText(btn.closest(".bp-code").querySelector("pre").textContent);
  btn.textContent = "已复制";
  setTimeout(() => {
    btn.textContent = T.copy;
  }, 1200);
}

function toggleDarkMode() {
  document.body.classList.toggle("theme-dark");
  localStorage.setItem("darkMode", document.body.classList.contains("theme-dark"));
}

function toggleSidebar() {
  document.body.classList.toggle("sidebar-open");
}

if (localStorage.getItem("darkMode") === "true") document.body.classList.add("theme-dark");
loadDoc().catch(err => {
  root.innerHTML = `<section class="bp-panel">${T.loadFail}：${esc(err.message)}</section>`;
});

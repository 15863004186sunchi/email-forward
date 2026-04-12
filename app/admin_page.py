"""
管理后台 HTML 页面

存放 ADMIN_PAGE_HTML 字符串，由 api.py 引用渲染。
"""

ADMIN_PAGE_HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>邮件转发管理后台</title>
<style>
:root{
  --primary:#4A7EF5;--primary-dark:#3A6EE0;
  --success:#22C55E;--danger:#EF4444;--warning:#F59E0B;
  --gray-50:#F9FAFB;--gray-100:#F3F4F6;--gray-200:#E5E7EB;
  --gray-500:#6B7280;--gray-700:#374151;--gray-900:#111827;
  --radius:8px;--radius-lg:12px;
  --shadow:0 1px 3px rgba(0,0,0,.1),0 1px 2px rgba(0,0,0,.06);
  --shadow-md:0 4px 6px rgba(0,0,0,.07),0 2px 4px rgba(0,0,0,.06);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#F0F2F5;min-height:100vh;color:var(--gray-700)}

/* ── 导航栏 ─────────────────────────────────────────────── */
.navbar{background:#fff;border-bottom:1px solid var(--gray-200);
        padding:0 24px;height:56px;display:flex;align-items:center;
        gap:24px;position:sticky;top:0;z-index:100;box-shadow:var(--shadow)}
.navbar-brand{font-size:16px;font-weight:700;color:var(--gray-900);
              display:flex;align-items:center;gap:8px;margin-right:auto}
.navbar-brand span{font-size:20px}
.nav-tab{padding:4px 12px;border-radius:6px;font-size:14px;cursor:pointer;
         color:var(--gray-500);transition:all .15s;border:none;background:none}
.nav-tab:hover{background:var(--gray-100);color:var(--gray-900)}
.nav-tab.active{background:#EEF2FF;color:var(--primary);font-weight:500}
.nav-btn{padding:6px 14px;border-radius:6px;font-size:13px;cursor:pointer;
         color:var(--danger);background:none;border:1px solid var(--gray-200);
         transition:all .15s}
.nav-btn:hover{background:#FEF2F2;border-color:var(--danger)}

/* ── 主内容区 ───────────────────────────────────────────── */
.main{max-width:1200px;margin:0 auto;padding:24px 24px}

/* ── 统计卡片 ───────────────────────────────────────────── */
.stat-row{display:flex;gap:16px;margin-bottom:24px;flex-wrap:wrap}
.stat-card{background:#fff;border-radius:var(--radius-lg);padding:20px 24px;
           box-shadow:var(--shadow);flex:1;min-width:140px}
.stat-value{font-size:32px;font-weight:700;color:var(--gray-900);margin-bottom:4px}
.stat-label{font-size:13px;color:var(--gray-500)}
.stat-card.blue  .stat-value{color:var(--primary)}
.stat-card.green .stat-value{color:#16A34A}
.stat-card.red   .stat-value{color:var(--danger)}
.stat-card.yellow .stat-value{color:#CA8A04}

/* ── 内容面板 ───────────────────────────────────────────── */
.panel{background:#fff;border-radius:var(--radius-lg);box-shadow:var(--shadow);
       display:none}
.panel.active{display:block}

.panel-header{padding:16px 20px;border-bottom:1px solid var(--gray-100);
              display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.panel-title{font-size:15px;font-weight:600;color:var(--gray-900);margin-right:auto}

/* ── 工具栏 ─────────────────────────────────────────────── */
.toolbar-search{border:1px solid var(--gray-200);border-radius:var(--radius);
                padding:7px 12px;font-size:14px;outline:none;width:220px;
                transition:border-color .15s}
.toolbar-search:focus{border-color:var(--primary)}
.toolbar-select{border:1px solid var(--gray-200);border-radius:var(--radius);
                padding:7px 10px;font-size:13px;outline:none;cursor:pointer;
                color:var(--gray-700);background:#fff}

/* ── 按钮 ───────────────────────────────────────────────── */
.btn{padding:7px 14px;border-radius:6px;font-size:13px;font-weight:500;
     cursor:pointer;border:none;transition:all .15s;display:inline-flex;
     align-items:center;gap:6px}
.btn-primary{background:var(--primary);color:#fff}
.btn-primary:hover{background:var(--primary-dark)}
.btn-primary:disabled{opacity:.6;cursor:not-allowed}
.btn-danger{background:transparent;color:var(--danger);
            border:1px solid var(--gray-200)}
.btn-danger:hover{background:#FEF2F2;border-color:var(--danger)}
.btn-ghost{background:transparent;color:var(--gray-500);
           border:1px solid var(--gray-200)}
.btn-ghost:hover{background:var(--gray-100)}

/* ── 表格 ───────────────────────────────────────────────── */
.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;padding:10px 14px;background:var(--gray-50);
   color:var(--gray-500);font-weight:500;font-size:12px;
   text-transform:uppercase;letter-spacing:.04em;
   border-bottom:1px solid var(--gray-200)}
td{padding:12px 14px;border-bottom:1px solid var(--gray-100);
   color:var(--gray-700)}
tr:last-child td{border-bottom:none}
tr:hover td{background:var(--gray-50)}
.expand-row td{background:#FEF2F2;font-size:13px;color:var(--danger);padding:8px 14px}

/* ── 徽标 ───────────────────────────────────────────────── */
.badge{display:inline-flex;align-items:center;gap:4px;padding:2px 10px;
       border-radius:999px;font-size:12px;font-weight:500}
.badge-green {background:#DCFCE7;color:#16A34A}
.badge-yellow{background:#FEF9C3;color:#CA8A04}
.badge-gray  {background:#F3F4F6;color:#6B7280}
.badge-red   {background:#FEE2E2;color:#DC2626}
.badge-orange{background:#FEF3C7;color:#D97706}

/* ── Modal ──────────────────────────────────────────────── */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.45);
               display:none;align-items:center;justify-content:center;z-index:1000}
.modal-overlay.open{display:flex}
.modal{background:#fff;border-radius:var(--radius-lg);padding:28px;
       width:100%;max-width:420px;box-shadow:0 20px 60px rgba(0,0,0,.15)}
.modal-title{font-size:17px;font-weight:600;margin-bottom:20px;
             display:flex;justify-content:space-between;align-items:center}
.modal-close{cursor:pointer;color:var(--gray-500);font-size:18px;
             background:none;border:none;line-height:1}
.form-group{margin-bottom:14px}
.form-label{display:block;font-size:13px;font-weight:500;
            color:var(--gray-700);margin-bottom:6px}
.form-input{width:100%;border:1px solid var(--gray-200);border-radius:var(--radius);
            padding:9px 12px;font-size:14px;outline:none;transition:border .15s}
.form-input:focus{border-color:var(--primary)}
.modal-footer{display:flex;gap:10px;justify-content:flex-end;margin-top:20px}

/* ── 自动刷新开关 ───────────────────────────────────────── */
.switch{position:relative;display:inline-block;width:36px;height:20px}
.switch input{opacity:0;width:0;height:0}
.slider{position:absolute;cursor:pointer;inset:0;background:var(--gray-200);
        border-radius:20px;transition:.2s}
.slider:before{position:absolute;content:"";height:14px;width:14px;
               left:3px;bottom:3px;background:#fff;border-radius:50%;transition:.2s}
input:checked + .slider{background:var(--primary)}
input:checked + .slider:before{transform:translateX(16px)}

/* ── 空状态 ─────────────────────────────────────────────── */
.empty{text-align:center;padding:48px 24px;color:var(--gray-500)}
.empty svg{margin-bottom:12px;opacity:.4}

/* ── 登录 overlay ───────────────────────────────────────── */
.login-overlay{position:fixed;inset:0;background:rgba(15,23,42,.85);
               display:flex;align-items:center;justify-content:center;z-index:999}
.login-card{background:#fff;border-radius:var(--radius-lg);padding:36px 40px;
            width:100%;max-width:380px;text-align:center}
.login-card h2{font-size:20px;font-weight:700;margin-bottom:8px}
.login-card p{font-size:14px;color:var(--gray-500);margin-bottom:24px}
.login-error{color:var(--danger);font-size:13px;margin-top:10px;display:none}
</style>
</head>
<body>

<!-- ── 登录 overlay ──────────────────────────────────────── -->
<div class="login-overlay" id="loginOverlay">
  <div class="login-card">
    <div style="font-size:36px;margin-bottom:12px">📬</div>
    <h2>邮件转发管理后台</h2>
    <p>请输入管理员 API Key 以继续</p>
    <input type="password" class="form-input" id="loginInput"
           placeholder="API Key..." style="text-align:center"
           onkeydown="if(event.key==='Enter')doLogin()">
    <button class="btn btn-primary" style="width:100%;margin-top:12px;justify-content:center"
            onclick="doLogin()">进入后台</button>
    <div class="login-error" id="loginErr">❌ API Key 不正确，请重试</div>
  </div>
</div>

<!-- ── 导航栏 ─────────────────────────────────────────────── -->
<nav class="navbar">
  <div class="navbar-brand"><span>📬</span>邮件转发管理后台</div>
  <button class="nav-tab active" onclick="switchTab('routes',this)">邮箱路由</button>
  <button class="nav-tab" onclick="switchTab('logs',this)">转发日志</button>
  <button class="nav-btn" onclick="logout()">退出</button>
</nav>

<div class="main">

  <!-- ── 统计卡片 ─────────────────────────────────────────── -->
  <div class="stat-row">
    <div class="stat-card blue"><div class="stat-value" id="s-total">—</div><div class="stat-label">总邮箱数</div></div>
    <div class="stat-card green"><div class="stat-value" id="s-active">—</div><div class="stat-label">已激活</div></div>
    <div class="stat-card yellow"><div class="stat-value" id="s-pending">—</div><div class="stat-label">待设置</div></div>
    <div class="stat-card"><div class="stat-value" id="s-free">—</div><div class="stat-label">空闲</div></div>
    <div class="stat-card green"><div class="stat-value" id="s-today-ok">—</div><div class="stat-label">今日转发成功</div></div>
    <div class="stat-card red"><div class="stat-value" id="s-today-fail">—</div><div class="stat-label">今日转发失败</div></div>
  </div>

  <!-- ── 邮箱路由面板 ────────────────────────────────────── -->
  <div class="panel active" id="panel-routes">
    <div class="panel-header">
      <span class="panel-title">邮箱路由</span>
      <input type="text" class="toolbar-search" id="routeSearch" placeholder="搜索邮箱/订单/买家..." oninput="renderRoutes()">
      <select class="toolbar-select" id="routeStatus" onchange="renderRoutes()">
        <option value="all">全部状态</option>
        <option value="active">已激活</option>
        <option value="pending">待设置</option>
        <option value="free">空闲</option>
      </select>
      <button class="btn btn-primary" onclick="openAssignModal()">+ 分配邮箱</button>
      <button class="btn btn-ghost" onclick="loadAll()">↻ 刷新</button>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>邮箱地址</th><th>转发目标</th><th>买家 / 订单</th>
            <th>状态</th><th>设置链接</th><th>操作</th>
          </tr>
        </thead>
        <tbody id="routesTbody"></tbody>
      </table>
    </div>
  </div>

  <!-- ── 转发日志面板 ────────────────────────────────────── -->
  <div class="panel" id="panel-logs">
    <div class="panel-header">
      <span class="panel-title">转发日志（最近 200 条）</span>
      <input type="text" class="toolbar-search" id="logSearch" placeholder="搜索邮箱/发件人..." oninput="renderLogs()">
      <select class="toolbar-select" id="logStatus" onchange="renderLogs()">
        <option value="all">全部</option>
        <option value="success">成功</option>
        <option value="failed">失败</option>
        <option value="no_route">无路由</option>
      </select>
      <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--gray-500)">
        自动刷新
        <label class="switch"><input type="checkbox" id="autoRefresh" onchange="toggleAuto()"><span class="slider"></span></label>
      </label>
      <button class="btn btn-ghost" onclick="loadAll()">↻ 刷新</button>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>时间</th><th>收件邮箱</th><th>发件人</th><th>主题</th><th>状态</th><th>备注</th>
          </tr>
        </thead>
        <tbody id="logsTbody"></tbody>
      </table>
    </div>
  </div>

</div>

<!-- ── 分配邮箱 Modal ──────────────────────────────────────── -->
<div class="modal-overlay" id="assignModal">
  <div class="modal">
    <div class="modal-title">分配邮箱<button class="modal-close" onclick="closeModal()">✕</button></div>
    <div class="form-group">
      <label class="form-label">邮箱前缀 <span style="color:var(--danger)">*</span></label>
      <input type="text" class="form-input" id="m-local" placeholder="如 shop001">
    </div>
    <div class="form-group">
      <label class="form-label">订单 ID <span style="color:var(--danger)">*</span></label>
      <input type="text" class="form-input" id="m-order" placeholder="ORDER_001">
    </div>
    <div class="form-group">
      <label class="form-label">买家名称</label>
      <input type="text" class="form-input" id="m-name" placeholder="张三（可选）">
    </div>
    <div id="m-error" style="color:var(--danger);font-size:13px;margin-top:4px;display:none"></div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">取消</button>
      <button class="btn btn-primary" id="m-submit" onclick="doAssign()">确认分配</button>
    </div>
  </div>
</div>

<script>
// ── 状态 ─────────────────────────────────────────────────
const state = {
  apiKey: localStorage.getItem('admin_api_key') || '',
  routes: [],
  logs: [],
  autoTimer: null,
  domain: '{{ domain }}',
  vpsHost: location.host,
};

// ── 登录 ─────────────────────────────────────────────────
async function doLogin() {
  const key = document.getElementById('loginInput').value.trim();
  if (!key) return;
  // 验证：尝试调用 list 接口
  const res = await fetch('/api/email/list', { headers: {'X-API-Key': key} });
  if (res.ok) {
    state.apiKey = key;
    localStorage.setItem('admin_api_key', key);
    document.getElementById('loginOverlay').style.display = 'none';
    loadAll();
  } else {
    document.getElementById('loginErr').style.display = 'block';
  }
}
function logout() {
  localStorage.removeItem('admin_api_key');
  location.reload();
}

// ── API ──────────────────────────────────────────────────
const API = {
  async get(path) {
    const r = await fetch(path, { headers: {'X-API-Key': state.apiKey} });
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: 'POST',
      headers: {'X-API-Key': state.apiKey, 'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    return r.json();
  }
};

async function loadAll() {
  const [rd, ld] = await Promise.all([
    API.get('/api/email/list'),
    API.get('/api/email/logs'),
  ]);
  state.routes = rd.routes || [];
  state.logs   = ld.logs || [];
  renderStats();
  renderRoutes();
  renderLogs();
}

// ── Tab 切换 ─────────────────────────────────────────────
function switchTab(tab, el) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + tab).classList.add('active');
}

// ── 统计 ─────────────────────────────────────────────────
function renderStats() {
  const r = state.routes;
  const total   = r.length;
  const active  = r.filter(x => x.active).length;
  const pending = r.filter(x => !x.active && x.order_id).length;
  const free    = r.filter(x => !x.order_id).length;

  const today = new Date().toDateString();
  const todayLogs = state.logs.filter(l => new Date(l.time).toDateString() === today);
  const ok   = todayLogs.filter(l => l.status === 'success').length;
  const fail = todayLogs.filter(l => l.status === 'failed').length;

  set('s-total', total);
  set('s-active', active);
  set('s-pending', pending);
  set('s-free', free);
  set('s-today-ok', ok);
  set('s-today-fail', fail);
}
function set(id, v) { document.getElementById(id).textContent = v; }

// ── 邮箱路由表格 ─────────────────────────────────────────
function routeStatus(r) {
  if (r.active)                     return ['badge-green', '✅ 已激活'];
  if (!r.active && r.order_id)      return ['badge-yellow', '⏳ 待设置'];
  return ['badge-gray', '⬜ 空闲'];
}

function renderRoutes() {
  const kw   = (document.getElementById('routeSearch').value || '').toLowerCase();
  const sf   = document.getElementById('routeStatus').value;
  let rows   = state.routes;

  if (kw) rows = rows.filter(r =>
    r.local_part.includes(kw) || (r.order_id||'').toLowerCase().includes(kw) ||
    (r.buyer_name||'').toLowerCase().includes(kw) || (r.forward_to||'').toLowerCase().includes(kw)
  );
  if (sf === 'active')  rows = rows.filter(r => r.active);
  if (sf === 'pending') rows = rows.filter(r => !r.active && r.order_id);
  if (sf === 'free')    rows = rows.filter(r => !r.order_id);

  const tbody = document.getElementById('routesTbody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="6"><div class="empty">暂无数据</div></td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const [cls, label] = routeStatus(r);
    const setupLink = r.order_id
      ? `<a href="/setup?e=${r.local_part}&o=${r.order_id}" target="_blank"
            style="font-size:12px;color:var(--primary)">打开 →</a>`
      : '—';
    const opBtn = r.order_id
      ? `<button class="btn btn-danger" onclick="doRelease('${r.local_part}')">释放</button>`
      : '—';
    return `<tr>
      <td><b>${r.local_part}</b>@${state.domain}</td>
      <td>${r.forward_to || '<span style="color:var(--gray-500)">未设置</span>'}</td>
      <td>${r.buyer_name||'未分配'} / <span style="color:var(--gray-500)">${r.order_id||'—'}</span></td>
      <td><span class="badge ${cls}">${label}</span></td>
      <td>${setupLink}</td>
      <td>${opBtn}</td>
    </tr>`;
  }).join('');
}

// ── 日志表格 ─────────────────────────────────────────────
function logBadge(status) {
  if (status === 'success')  return ['badge-green', '✅ 成功'];
  if (status === 'failed')   return ['badge-red',   '❌ 失败'];
  return ['badge-orange', '⚠️ 无路由'];
}

function renderLogs() {
  const kw = (document.getElementById('logSearch').value || '').toLowerCase();
  const sf = document.getElementById('logStatus').value;
  let rows = state.logs;

  if (kw) rows = rows.filter(l =>
    (l.local_part||'').includes(kw) || (l.from_addr||'').toLowerCase().includes(kw) ||
    (l.subject||'').toLowerCase().includes(kw)
  );
  if (sf !== 'all') rows = rows.filter(l => l.status === sf);

  const tbody = document.getElementById('logsTbody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="6"><div class="empty">暂无日志</div></td></tr>';
    return;
  }
  tbody.innerHTML = rows.map((l, i) => {
    const [cls, label] = logBadge(l.status);
    const t = new Date(l.time + 'Z');
    const timeStr = isNaN(t) ? l.time : t.toLocaleString('zh-CN');
    const note = l.forward_to ? `→ ${l.forward_to}` : '—';
    const expandBtn = l.status === 'failed'
      ? `onclick="toggleExpand(${i}, this)" style="cursor:pointer"` : '';
    return `<tr ${expandBtn} id="logrow-${i}">
      <td style="white-space:nowrap;font-size:12px">${timeStr}</td>
      <td>${l.local_part}@${state.domain}</td>
      <td style="font-size:13px">${l.from_addr||'—'}</td>
      <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
          title="${(l.subject||'').replace(/"/g,'&quot;')}">${l.subject||'（无主题）'}</td>
      <td><span class="badge ${cls}">${label}</span></td>
      <td style="font-size:13px;color:var(--gray-500)">${note}</td>
    </tr>${l.status === 'failed' ? `
    <tr class="expand-row" id="logerr-${i}" style="display:none">
      <td colspan="6">⚠ 错误详情：${l.error||'未知错误'}</td>
    </tr>` : ''}`;
  }).join('');
}

function toggleExpand(i, el) {
  const row = document.getElementById('logerr-' + i);
  if (row) row.style.display = row.style.display === 'none' ? 'table-row' : 'none';
}

// ── 释放邮箱 ─────────────────────────────────────────────
async function doRelease(localPart) {
  if (!confirm(`确认释放邮箱 ${localPart}@${state.domain}？\\n\\n释放后该邮箱转发规则将被删除，订单将无法再使用此邮箱。`)) return;
  const d = await API.post('/api/email/release', {local_part: localPart});
  if (d.success) { loadAll(); }
  else { alert('释放失败: ' + (d.error || '未知错误')); }
}

// ── 分配邮箱 Modal ────────────────────────────────────────
function openAssignModal() {
  ['m-local','m-order','m-name'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('m-error').style.display = 'none';
  document.getElementById('assignModal').classList.add('open');
}
function closeModal() {
  document.getElementById('assignModal').classList.remove('open');
}
async function doAssign() {
  const local = document.getElementById('m-local').value.trim();
  const order = document.getElementById('m-order').value.trim();
  const name  = document.getElementById('m-name').value.trim();
  const errEl = document.getElementById('m-error');

  if (!local || !order) {
    errEl.textContent = '邮箱前缀和订单 ID 为必填项';
    errEl.style.display = 'block';
    return;
  }

  const btn = document.getElementById('m-submit');
  btn.disabled = true; btn.textContent = '分配中...';
  const d = await API.post('/api/email/assign', {
    local_part: local, order_id: order, buyer_name: name
  });
  btn.disabled = false; btn.textContent = '确认分配';

  if (d.success) {
    closeModal();
    await loadAll();
  } else {
    errEl.textContent = '❌ ' + (d.error || '分配失败');
    errEl.style.display = 'block';
  }
}

// ── 自动刷新 ─────────────────────────────────────────────
function toggleAuto() {
  const on = document.getElementById('autoRefresh').checked;
  if (on) { state.autoTimer = setInterval(loadAll, 30000); }
  else    { clearInterval(state.autoTimer); }
}

// ── 初始化 ───────────────────────────────────────────────
if (state.apiKey) {
  document.getElementById('loginOverlay').style.display = 'none';
  loadAll();
}
</script>
</body>
</html>"""

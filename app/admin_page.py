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
  <button class="nav-tab active" id="tab-routes-btn" onclick="switchTab('routes',this)">邮箱路由</button>
  <button class="nav-tab" id="tab-inventory-btn" onclick="switchTab('inventory',this)">邮箱库存</button>
  <button class="nav-tab" id="tab-logs-btn" onclick="switchTab('logs',this)">转发日志</button>
  <button class="nav-btn" onclick="logout()">退出账户</button>
</nav>

<div class="main">

  <!-- ── 统计卡片 ─────────────────────────────────────────── -->
  <div class="stat-row">
    <div class="stat-card blue"><div class="stat-value" id="s-total">—</div><div class="stat-label">库存在线</div></div>
    <div class="stat-card green"><div class="stat-value" id="s-active">—</div><div class="stat-label">已激活路由</div></div>
    <div class="stat-card yellow"><div class="stat-value" id="s-pending">—</div><div class="stat-label">待设置路由</div></div>
    <div class="stat-card"><div class="stat-value" id="s-free">—</div><div class="stat-label">待售空闲</div></div>
    <div class="stat-card green"><div class="stat-value" id="s-today-ok">—</div><div class="stat-label">今日转发成功</div></div>
    <div class="stat-card red"><div class="stat-value" id="s-today-fail">—</div><div class="stat-label">今日转发失败</div></div>
  </div>

  <!-- ── 邮箱路由面板 ────────────────────────────────────── -->
  <div class="panel active" id="panel-routes">
    <div class="panel-header">
      <span class="panel-title">路由记录</span>
      <input type="text" class="toolbar-search" id="routeSearch" placeholder="搜索邮箱/订单/买家..." oninput="renderRoutes()">
      <select class="toolbar-select" id="routeStatus" onchange="renderRoutes()">
        <option value="all">显示全部</option>
        <option value="active">已激活</option>
        <option value="pending">待设置</option>
      </select>
      <button class="btn btn-primary" onclick="openBatchAssignModal()">批量分配测试邮箱</button>
      <button class="btn btn-ghost" onclick="loadAll()">↻ 刷新</button>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>邮箱地址</th><th>转发目标</th><th>买家/订单</th>
            <th>状态</th><th>设置链接</th><th>操作</th>
          </tr>
        </thead>
        <tbody id="routesTbody"></tbody>
      </table>
    </div>
  </div>

  <!-- ── 邮箱库存面板 ────────────────────────────────────── -->
  <div class="panel" id="panel-inventory">
    <div class="panel-header">
      <span class="panel-title">库存管理</span>
      <input type="text" class="toolbar-search" id="invSearch" placeholder="搜索前缀..." oninput="renderInventory()">
      <button class="btn btn-primary" onclick="openAddPoolModal()">+ 增加库存</button>
      <button class="btn btn-ghost" onclick="loadAll()">↻ 刷新</button>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>前缀(ID)</th><th>完整地址</th><th>当前状态</th><th>对应订单</th><th>操作</th>
          </tr>
        </thead>
        <tbody id="invTbody"></tbody>
      </table>
    </div>
  </div>

  <!-- ── 转发日志面板 ────────────────────────────────────── -->
  <div class="panel" id="panel-logs">
    <div class="panel-header">
      <span class="panel-title">实时转发日志</span>
      <input type="text" class="toolbar-search" id="logSearch" placeholder="搜索关键字..." oninput="renderLogs()">
      <label style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--gray-500)">
        自动刷新
        <label class="switch"><input type="checkbox" id="autoRefresh" onchange="toggleAuto()"><span class="slider"></span></label>
      </label>
      <button class="btn btn-ghost" onclick="loadAll()">↻ 刷新内容</button>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>时间</th><th>收件人</th><th>原始发信方</th><th>主题内容</th><th>转发状态</th><th>备注</th>
          </tr>
        </thead>
        <tbody id="logsTbody"></tbody>
      </table>
    </div>
  </div>

</div>

<!-- ── 批量分配 Modal ──────────────────────────────────────── -->
<div class="modal-overlay" id="batchAssignModal">
  <div class="modal">
    <div class="modal-title">批量分配随机库存<button class="modal-close" onclick="closeModals()">✕</button></div>
    <p style="font-size:12px;color:var(--gray-500);margin-bottom:16px">系统将从剩余空闲邮箱中随机抽取指定数量并分配。</p>
    <div class="form-group">
      <label class="form-label">分配数量 (1-50)</label>
      <input type="number" class="form-input" id="ba-count" value="1" min="1" max="50">
    </div>
    <div class="form-group">
      <label class="form-label">统一转发到 (目标邮箱)</label>
      <input type="email" class="form-input" id="ba-target" placeholder="example@qq.com">
    </div>
    <div class="form-group">
      <label class="form-label">备注名称 (可选)</label>
      <input type="text" class="form-input" id="ba-name" placeholder="批量测试分配">
    </div>
    <div id="ba-error" style="color:var(--danger);font-size:13px;margin-top:4px;display:none"></div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModals()">取消</button>
      <button class="btn btn-primary" id="ba-submit" onclick="doBatchAssign()">开始分配</button>
    </div>
  </div>
</div>

<!-- ── 录入库存 Modal ──────────────────────────────────────── -->
<div class="modal-overlay" id="addPoolModal">
  <div class="modal">
    <div class="modal-title">增加邮箱库存<button class="modal-close" onclick="closeModals()">✕</button></div>
    <div class="form-group">
      <label class="form-label" style="display:flex;justify-content:space-between">
        输入前缀 (每行一个)
        <a href="javascript:void(0)" onclick="doGenerateNames()" style="color:var(--primary);font-size:12px;text-decoration:none">✨ 随机生成真人名</a>
      </label>
      <textarea class="form-input" id="ap-list" rows="10" placeholder="mail1001\nmail1002\n..."></textarea>
    </div>
    <p style="font-size:12px;color:var(--gray-500)">重复录入的前缀将被自动过滤。</p>
    <div id="ap-error" style="color:var(--danger);font-size:13px;margin-top:4px;display:none"></div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModals()">取消</button>
      <button class="btn btn-primary" id="ap-submit" onclick="doAddPool()">确认录入</button>
    </div>
  </div>
</div>

<script>
// ── 核心状态 ─────────────────────────────────────────────
const state = {
  apiKey: localStorage.getItem('admin_api_key') || '',
  routes: [],
  logs: [],
  autoTimer: null,
  domain: '{{ domain }}',
};

// ── 鉴权逻辑 ─────────────────────────────────────────────
async function doLogin() {
  const key = document.getElementById('loginInput').value.trim();
  if (!key) return;
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

// ── 数据交互 ─────────────────────────────────────────────
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
  if (!state.apiKey) return;
  const [rd, ld] = await Promise.all([
    API.get('/api/email/list'),
    API.get('/api/email/logs'),
  ]);
  state.routes = rd.routes || [];
  state.logs   = ld.logs || [];
  renderStats();
  renderRoutes();
  renderInventory();
  renderLogs();
}

// ── UI 渲染逻辑 ──────────────────────────────────────────
function switchTab(tab, el) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + tab).classList.add('active');
}

function renderStats() {
  const r = state.routes;
  const total = r.length;
  const active = r.filter(x => x.active).length;
  const pending = r.filter(x => !x.active && x.order_id).length;
  const free = r.filter(x => !x.order_id).length;

  const today = new Date().toDateString();
  const todayLogs = state.logs.filter(l => new Date(l.time).toDateString() === today);
  const ok = todayLogs.filter(l => l.status === 'success').length;
  const fail = todayLogs.filter(l => l.status === 'failed').length;

  set('s-total', total); set('s-active', active); set('s-pending', pending);
  set('s-free', free); set('s-today-ok', ok); set('s-today-fail', fail);
}
function set(id, v) { document.getElementById(id).textContent = v; }

function renderRoutes() {
  const kw = (document.getElementById('routeSearch').value || '').toLowerCase();
  const sf = document.getElementById('routeStatus').value;
  let rows = state.routes.filter(r => r.order_id); // 路由页只显示已分配的

  if (kw) rows = rows.filter(r =>
    r.local_part.includes(kw) || (r.order_id||'').toLowerCase().includes(kw) ||
    (r.buyer_name||'').toLowerCase().includes(kw) || (r.forward_to||'').toLowerCase().includes(kw)
  );
  if (sf === 'active') rows = rows.filter(r => r.active);
  if (sf === 'pending') rows = rows.filter(r => !r.active);

  const tbody = document.getElementById('routesTbody');
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty">暂无相关路由记录</div></td></tr>'; return; }
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><b>${r.local_part}</b>@${state.domain}</td>
      <td>${r.forward_to || '<span style="color:var(--gray-500)">尚未设置</span>'}</td>
      <td>${r.buyer_name || '—'} / <span style="font-size:12px;color:var(--gray-500)">${r.order_id}</span></td>
      <td><span class="badge ${r.active?'badge-green':'badge-yellow'}">${r.active?'✅ 已激活':'⏳ 待设置'}</span></td>
      <td><a href="/setup?e=${r.local_part}&o=${r.order_id}" target="_blank" style="color:var(--primary);font-size:12px">打开设置页</a></td>
      <td><button class="btn btn-danger" onclick="doRelease('${r.local_part}')">释放</button></td>
    </tr>
  `).join('');
}

function renderInventory() {
  const kw = (document.getElementById('invSearch').value || '').toLowerCase();
  let rows = state.routes;

  if (kw) rows = rows.filter(r => r.local_part.includes(kw));

  const tbody = document.getElementById('invTbody');
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty">库存为空，请增加前缀</div></td></tr>'; return; }
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td><code>${r.local_part}</code></td>
      <td>${r.local_part}@${state.domain}</td>
      <td><span class="badge ${r.order_id?'badge-orange':'badge-gray'}">${r.order_id?'已占用':'空闲'}</span></td>
      <td style="font-size:12px;color:var(--gray-500)">${r.order_id || '—'}</td>
      <td>${!r.order_id ? `<button class="btn btn-ghost" onclick="doDeletePool('${r.local_part}')" style="color:var(--danger)">删除</button>` : '—'}</td>
    </tr>
  `).join('');
}

function renderLogs() {
  const kw = (document.getElementById('logSearch').value || '').toLowerCase();
  let rows = state.logs;
  if (kw) rows = rows.filter(l => (l.local_part||'').includes(kw) || (l.from_addr||'').toLowerCase().includes(kw) || (l.subject||'').toLowerCase().includes(kw));
  const tbody = document.getElementById('logsTbody');
  if (!rows.length) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty">暂无实时日志</div></td></tr>'; return; }
  tbody.innerHTML = rows.map(l => {
    const s = l.status === 'success' ? ['badge-green', '成功'] : ['badge-red', '失败'];
    return `<tr>
      <td style="font-size:11px;color:var(--gray-500)">${l.time.split('.')[0].replace('T',' ')}</td>
      <td>${l.local_part}@${state.domain}</td>
      <td style="font-size:12px">${l.from_addr}</td>
      <td title="${l.subject}" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${l.subject||'—'}</td>
      <td><span class="badge ${s[0]}">${s[1]}</span></td>
      <td style="font-size:12px;color:var(--gray-500)">${l.forward_to?'→ '+l.forward_to : (l.error||'')}</td>
    </tr>`;
  }).join('');
}

// ── 交互操作 ─────────────────────────────────────────────
function closeModals() {
  document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('open'));
}

async function doRelease(lp) {
  if (!confirm(`确认重置 ${lp} 到空闲状态？\\n这会清除现有的转发规则和订单绑定。`)) return;
  const d = await API.post('/api/email/release', {local_part: lp});
  if (d.success) loadAll(); else alert(d.error);
}

// 批量分配
function openBatchAssignModal() {
  document.getElementById('ba-error').style.display='none';
  document.getElementById('batchAssignModal').classList.add('open');
}
async function doBatchAssign() {
  const count = document.getElementById('ba-count').value;
  const target = document.getElementById('ba-target').value.trim();
  const name = document.getElementById('ba-name').value.trim();
  if(!target) { alert('请输入目标邮箱'); return; }
  const btn = document.getElementById('ba-submit');
  btn.disabled = true; btn.textContent = '分配中...';
  const d = await API.post('/api/email/batch-assign', {count, forward_to: target, buyer_name: name});
  btn.disabled = false; btn.textContent = '开始分配';
  if (d.success) { closeModals(); loadAll(); }
  else { document.getElementById('ba-error').textContent = '❌ ' + d.error; document.getElementById('ba-error').style.display='block'; }
}

// 库存增删
function openAddPoolModal() {
  document.getElementById('ap-error').style.display='none';
  document.getElementById('ap-list').value = '';
  document.getElementById('addPoolModal').classList.add('open');
}
async function doAddPool() {
  const list = document.getElementById('ap-list').value;
  if(!list.trim()) return;
  const btn = document.getElementById('ap-submit');
  btn.disabled = true; btn.textContent = '录入中...';
  const d = await API.post('/api/pool/add', {local_parts: list});
  btn.disabled = false; btn.textContent = '确认录入';
  if (d.success) { closeModals(); loadAll(); }
  else { alert(d.error); }
}

async function doGenerateNames() {
  const btn = document.querySelector('[onclick="doGenerateNames()"]');
  const orgText = btn.innerHTML;
  btn.innerHTML = '生成中...';
  try {
    const d = await API.get('/api/pool/generate-names?count=50');
    if (d.success) {
      const area = document.getElementById('ap-list');
      const existing = area.value.trim();
      area.value = (existing ? existing + '\n' : '') + d.names.join('\n');
    }
  } catch (e) { alert('生成失败: ' + e); }
  btn.innerHTML = orgText;
}

async function doDeletePool(lp) {
  if(!confirm(`确认从库存永久删除前缀 ${lp}？`)) return;
  const d = await API.post('/api/pool/delete', {local_part: lp});
  if (d.success) loadAll(); else alert(d.error);
}

function toggleAuto() {
  const on = document.getElementById('autoRefresh').checked;
  if(on) state.autoTimer = setInterval(loadAll, 10000);
  else clearInterval(state.autoTimer);
}

if (state.apiKey) loadAll();
</script>
</body>
</html>"""

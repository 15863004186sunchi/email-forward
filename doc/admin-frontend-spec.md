# 邮件转发系统 — 前端与管理后台实现文档

> 本文档面向 AI 编程助手（Gemini / Codex）或前端开发者，描述需要实现的两个界面：
> 1. **用户设置页**（`/setup`）：用户设置/修改自己的转发邮箱
> 2. **管理后台**（`/admin`）：管理员可视化管理所有邮箱路由与日志
>
> 技术栈：纯 HTML + CSS + Vanilla JS（单文件，内嵌到 `api.py` 的 `render_template_string`），无需引入前端框架。
> 也可以拆成独立 HTML 文件放在 `app/templates/` 目录，Flask 用 `render_template` 渲染。

---

## 一、项目现状

### 后端已有接口

所有接口均已实现，文档详见主方案 README，此处列出本次前端涉及的接口：

#### 用户接口（无需 API Key）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/email/info?local_part=xxx&order_id=yyy` | 查询当前转发设置 |
| POST | `/api/email/set-forward` | 设置/修改转发邮箱 |

#### 管理接口（需要 Header: `X-API-Key: YOUR_KEY`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/email/list` | 列出所有邮箱路由 |
| GET | `/api/email/logs` | 获取转发日志（最近 200 条） |
| POST | `/api/email/assign` | 分配邮箱给订单 |
| POST | `/api/email/release` | 释放邮箱 |

#### 响应格式示例

```json
// GET /api/email/list
{
  "success": true,
  "routes": [
    {
      "local_part": "abc123",
      "email": "abc123@flapysun.com",
      "forward_to": "user@gmail.com",
      "active": true,
      "order_id": "ORDER_001",
      "buyer_name": "张三"
    }
  ]
}

// GET /api/email/logs
{
  "success": true,
  "logs": [
    {
      "local_part": "abc123",
      "from_addr": "sender@example.com",
      "forward_to": "user@gmail.com",
      "subject": "你好",
      "status": "success",
      "error": null,
      "time": "2024-01-01T12:00:00"
    }
  ]
}
```

---

## 二、用户设置页（`/setup`）

### 访问方式

```
http://YOUR_VPS/setup?e=abc123&o=ORDER_001
```

URL 参数：
- `e`：邮箱前缀（local_part），如 `abc123`
- `o`：订单 ID，用于身份校验

### 页面功能

1. 页面加载时，用 `e` 和 `o` 参数调用 `GET /api/email/info` 查询当前设置
2. 展示用户的专属邮箱地址（只读）
3. 提供输入框让用户填写/修改转发目标邮箱
4. 点击保存后调用 `POST /api/email/set-forward`，展示成功/失败提示
5. 参数缺失或订单不存在时展示错误状态页

### UI 设计要求

- 风格：简洁现代，白色卡片居中，圆角阴影
- 配色：主色 `#4A7EF5`（蓝），成功 `#22C55E`（绿），错误 `#EF4444`（红）
- 字体：系统默认字体栈（`-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`）
- 移动端适配：`max-width: 480px`，`padding: 24px`

### 页面结构（线框图）

```
┌─────────────────────────────────────┐
│  Logo / 系统名称（可选）              │
│                                     │
│  ┌─────────────────────────────┐    │
│  │  📬  设置转发邮箱             │    │
│  │                             │    │
│  │  您的专属邮箱                │    │
│  │  ┌─────────────────────┐   │    │
│  │  │ abc123@flapysun.com │   │    │  ← 只读，蓝色背景
│  │  └─────────────────────┘   │    │
│  │                             │    │
│  │  转发到（您自己的邮箱）        │    │
│  │  ┌─────────────────────┐   │    │
│  │  │ user@gmail.com      │   │    │  ← 可编辑输入框
│  │  └─────────────────────┘   │    │
│  │                             │    │
│  │  ┌─────────────────────┐   │    │
│  │  │     保存设置  →      │   │    │  ← 主色按钮，加载中禁用
│  │  └─────────────────────┘   │    │
│  │                             │    │
│  │  ✓ 设置成功！               │    │  ← 状态提示（默认隐藏）
│  └─────────────────────────────┘    │
│                                     │
│  说明文字：设置后约 1 分钟内生效       │
└─────────────────────────────────────┘
```

### 交互细节

- 按钮点击后变为"保存中..."并禁用，请求完成后恢复
- 成功提示 3 秒后自动消失
- 邮箱格式前端验证：`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`
- 若 URL 缺少 `e` 或 `o` 参数，展示错误卡片："链接无效，请从订单页面重新进入"

### 代码实现要点

```html
<!-- Flask render_template_string 变量 -->
<!-- {{ domain }} 由后端传入，值为 MY_DOMAIN 环境变量 -->

<script>
  const params = new URLSearchParams(location.search);
  const localPart = params.get('e') || '';
  const orderId   = params.get('o') || '';

  // 页面加载：查询已有设置
  async function loadInfo() {
    const res = await fetch(`/api/email/info?local_part=${localPart}&order_id=${orderId}`);
    const d = await res.json();
    if (d.exists && d.forward_to) {
      document.getElementById('fwd').value = d.forward_to;
    }
  }

  // 保存
  async function save() {
    const forwardTo = document.getElementById('fwd').value.trim();
    // 前端验证邮箱格式
    // 调用 POST /api/email/set-forward
    // 处理成功/失败展示
  }
</script>
```

---

## 三、管理后台（`/admin`）

### 访问方式

```
http://YOUR_VPS/admin
```

页面加载时弹出 API Key 输入框（或从 localStorage 读取缓存的 Key）。
所有后续请求携带 `X-API-Key` 请求头。

### 整体布局

```
┌──────────────────────────────────────────────────────────────┐
│  顶部导航栏                                                    │
│  [系统图标] 邮件转发管理后台    [邮箱路由] [转发日志] [退出]     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  统计卡片行                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ 总邮箱数  │  │ 已激活   │  │ 今日转发  │  │ 转发失败  │    │
│  │   200    │  │   156    │  │    42    │  │    3     │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                                                              │
│  内容区（Tab 切换）                                           │
│  [邮箱路由 Tab]  [转发日志 Tab]                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Tab 1：邮箱路由管理

#### 功能列表

1. **搜索过滤**：按邮箱前缀、订单ID、买家名称实时过滤（前端过滤，无需请求接口）
2. **状态过滤**：下拉框选择"全部 / 已激活 / 未激活"
3. **数据表格**：展示所有路由
4. **操作**：每行可"释放邮箱"（调用 `/api/email/release`，二次确认）
5. **新增**：顶部"分配邮箱"按钮，弹出 Modal 填写信息

#### 表格结构

```
┌──────────────┬───────────────────────┬──────────────────────┬────────┬────────────┬───────────┬──────────┐
│ 邮箱地址     │ 转发目标              │ 买家 / 订单          │ 状态   │ 分配时间   │ 最后更新  │ 操作     │
├──────────────┼───────────────────────┼──────────────────────┼────────┼────────────┼───────────┼──────────┤
│ abc123@...   │ user@gmail.com        │ 张三 / ORDER_001     │ ✅激活 │ 2024-01-01 │ 2024-01-02│ [释放]   │
│ xyz456@...   │ —                     │ 李四 / ORDER_002     │ ⏳待设 │ 2024-01-02 │ —         │ [释放]   │
│ def789@...   │ —                     │ 未分配               │ ⬜空闲 │ —          │ —         │ —        │
└──────────────┴───────────────────────┴──────────────────────┴────────┴────────────┴───────────┴──────────┘
```

状态 Badge 样式：
- `✅ 已激活`：绿色背景 `#DCFCE7`，绿色文字 `#16A34A`
- `⏳ 待设置`：黄色背景 `#FEF9C3`，黄色文字 `#CA8A04`
- `⬜ 空闲`：灰色背景 `#F3F4F6`，灰色文字 `#6B7280`

#### 分配邮箱 Modal

```
┌──────────────────────────────────┐
│  分配邮箱                    [✕] │
├──────────────────────────────────┤
│  邮箱前缀 *                       │
│  ┌──────────────────────────┐   │
│  │ 输入 local_part，如 abc  │   │
│  └──────────────────────────┘   │
│                                  │
│  订单 ID *                        │
│  ┌──────────────────────────┐   │
│  │ ORDER_001                │   │
│  └──────────────────────────┘   │
│                                  │
│  买家名称                         │
│  ┌──────────────────────────┐   │
│  │ 张三                     │   │
│  └──────────────────────────┘   │
│                                  │
│  [取消]          [确认分配]       │
└──────────────────────────────────┘
```

### Tab 2：转发日志

#### 功能列表

1. **实时刷新**：页面顶部"刷新"按钮 + 可选自动刷新（30s 间隔，开关切换）
2. **状态过滤**：`全部 / 成功 / 失败 / 无路由`
3. **搜索**：按邮箱前缀或发件人过滤
4. **日志表格**：展示最近 200 条

#### 日志表格结构

```
┌────────────┬──────────────────┬────────────────────┬─────────────────────┬────────┬──────────────────────┐
│ 时间       │ 收件邮箱         │ 发件人             │ 主题                │ 状态   │ 备注                 │
├────────────┼──────────────────┼────────────────────┼─────────────────────┼────────┼──────────────────────┤
│ 12:01:32   │ abc123@...       │ boss@company.com   │ Q4 报告             │ ✅成功 │ → user@gmail.com     │
│ 11:58:10   │ xyz456@...       │ noreply@github.com │ PR merged           │ ❌失败 │ SMTP 连接超时         │
│ 11:30:05   │ unk999@...       │ spam@xxx.com       │ 广告                │ ⚠️无路由│ 邮箱未分配           │
└────────────┴──────────────────┴────────────────────┴─────────────────────┴────────┴──────────────────────┘
```

状态 Badge 样式：
- `✅ 成功`：绿色
- `❌ 失败`：红色，点击行可展开查看 `error` 详情
- `⚠️ 无路由`：橙色

#### 失败详情展开

点击失败行时，在该行下方展开一行：

```
┌─────────────────────────────────────────────────────────────────┐
│  错误详情：SMTPConnectError: Connection refused (111)            │
└─────────────────────────────────────────────────────────────────┘
```

### 顶部统计卡片数据来源

统计数据从 `/api/email/list` 和 `/api/email/logs` 的返回值前端计算得出：

```javascript
// 从 /api/email/list 计算
const total    = routes.length;
const active   = routes.filter(r => r.active).length;
const unset    = routes.filter(r => !r.active && r.order_id).length;
const free     = routes.filter(r => !r.order_id).length;

// 从 /api/email/logs 计算（当天日期过滤）
const today    = new Date().toDateString();
const todayLogs = logs.filter(l => new Date(l.time).toDateString() === today);
const todayOk  = todayLogs.filter(l => l.status === 'success').length;
const todayFail= todayLogs.filter(l => l.status === 'failed').length;
```

---

## 四、Flask 路由注册

在 `api.py` 中添加以下两个路由，返回对应 HTML：

```python
@app.route("/setup")
def setup_page():
    # 渲染用户设置页
    return render_template_string(USER_PAGE_HTML, domain=MY_DOMAIN)

@app.route("/admin")
def admin_page():
    # 渲染管理后台（API Key 由前端 JS 处理，不在服务端校验页面访问）
    return render_template_string(ADMIN_PAGE_HTML, domain=MY_DOMAIN)
```

其中 `USER_PAGE_HTML` 和 `ADMIN_PAGE_HTML` 是两个 Python 字符串变量，存放完整 HTML。
也可拆分为 `app/templates/setup.html` 和 `app/templates/admin.html`，用 `render_template` 加载。

---

## 五、样式规范

### CSS 变量（在 `:root` 中定义，便于统一修改）

```css
:root {
  --primary:      #4A7EF5;
  --primary-dark: #3A6EE0;
  --success:      #22C55E;
  --danger:       #EF4444;
  --warning:      #F59E0B;
  --gray-50:      #F9FAFB;
  --gray-100:     #F3F4F6;
  --gray-200:     #E5E7EB;
  --gray-500:     #6B7280;
  --gray-700:     #374151;
  --gray-900:     #111827;
  --radius:       8px;
  --radius-lg:    12px;
  --shadow:       0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06);
  --shadow-md:    0 4px 6px rgba(0,0,0,.07), 0 2px 4px rgba(0,0,0,.06);
}
```

### 通用组件样式

```css
/* 卡片 */
.card {
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 24px;
}

/* 主按钮 */
.btn-primary {
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: var(--radius);
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background .15s;
}
.btn-primary:hover    { background: var(--primary-dark); }
.btn-primary:disabled { opacity: .6; cursor: not-allowed; }

/* 危险按钮 */
.btn-danger {
  background: transparent;
  color: var(--danger);
  border: 1px solid var(--danger);
  border-radius: var(--radius);
  padding: 5px 12px;
  font-size: 13px;
  cursor: pointer;
}
.btn-danger:hover { background: #FEF2F2; }

/* 输入框 */
.input {
  width: 100%;
  border: 1px solid var(--gray-200);
  border-radius: var(--radius);
  padding: 9px 13px;
  font-size: 14px;
  outline: none;
  transition: border-color .15s;
}
.input:focus { border-color: var(--primary); }

/* Badge */
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}
.badge-green  { background: #DCFCE7; color: #16A34A; }
.badge-yellow { background: #FEF9C3; color: #CA8A04; }
.badge-gray   { background: #F3F4F6; color: #6B7280; }
.badge-red    { background: #FEE2E2; color: #DC2626; }
.badge-orange { background: #FEF3C7; color: #D97706; }

/* 表格 */
.table { width: 100%; border-collapse: collapse; font-size: 14px; }
.table th {
  text-align: left;
  padding: 10px 14px;
  background: var(--gray-50);
  color: var(--gray-500);
  font-weight: 500;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: .04em;
  border-bottom: 1px solid var(--gray-200);
}
.table td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--gray-100);
  color: var(--gray-700);
}
.table tr:hover td { background: var(--gray-50); }

/* 统计卡片 */
.stat-card {
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  box-shadow: var(--shadow);
  flex: 1;
  min-width: 140px;
}
.stat-card .stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--gray-900);
  margin-bottom: 4px;
}
.stat-card .stat-label {
  font-size: 13px;
  color: var(--gray-500);
}

/* Modal 遮罩 */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal {
  background: #fff;
  border-radius: var(--radius-lg);
  padding: 28px;
  width: 100%; max-width: 420px;
  box-shadow: 0 20px 60px rgba(0,0,0,.15);
}
```

---

## 六、前端 JS 架构建议

两个页面均使用原生 JS，无需框架，推荐以下组织方式：

```javascript
// ── 状态 ────────────────────────────────────────────────
const state = {
  apiKey: localStorage.getItem('admin_api_key') || '',
  routes: [],
  logs: [],
  filter: { status: 'all', keyword: '' },
  activeTab: 'routes',
  autoRefresh: false,
};

// ── API 调用层 ───────────────────────────────────────────
const API = {
  async get(path) {
    const res = await fetch(path, {
      headers: { 'X-API-Key': state.apiKey }
    });
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(path, {
      method: 'POST',
      headers: {
        'X-API-Key': state.apiKey,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    return res.json();
  }
};

// ── 渲染层 ──────────────────────────────────────────────
function renderRoutes() { /* 重新渲染表格 */ }
function renderLogs()   { /* 重新渲染日志 */ }
function renderStats()  { /* 重新渲染统计卡片 */ }

// ── 事件绑定 ─────────────────────────────────────────────
// 搜索框 oninput → 过滤 state.routes → renderRoutes()
// Tab 切换 → 更新 state.activeTab → 显示/隐藏对应区域
// 自动刷新 → setInterval(loadAll, 30000)
```

---

## 七、API Key 持久化

管理后台首次访问弹出输入框，Key 存入 `localStorage`：

```javascript
function getApiKey() {
  let key = localStorage.getItem('admin_api_key');
  if (!key) {
    key = prompt('请输入管理员 API Key：');
    if (key) localStorage.setItem('admin_api_key', key);
  }
  return key;
}

// 退出时清除
function logout() {
  localStorage.removeItem('admin_api_key');
  location.reload();
}
```

---

## 八、验收标准

### 用户设置页

- [ ] URL 参数缺失时展示错误提示，不崩溃
- [ ] 页面加载时自动填充已有转发邮箱
- [ ] 邮箱格式错误时前端阻止提交并提示
- [ ] 保存按钮加载中状态正常
- [ ] 成功/失败提示清晰可见
- [ ] 移动端 375px 宽度下正常显示

### 管理后台

- [ ] API Key 错误时提示"鉴权失败"
- [ ] 统计卡片数字正确（来自前端计算）
- [ ] 表格按关键词实时过滤
- [ ] 表格按状态过滤
- [ ] 释放邮箱有二次确认弹窗
- [ ] 分配邮箱 Modal 表单验证
- [ ] 转发日志失败行点击展开错误详情
- [ ] 自动刷新开关可用
- [ ] 空数据时展示"暂无数据"占位


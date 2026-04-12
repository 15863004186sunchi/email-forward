# 邮件自动转发商城 — 完整实现方案

## 一、需求背景

- 拥有 200 个邮箱地址（`*@flapysun.com`）
- 用户购买后获得全部 200 个邮箱
- 用户可自定义一个"目标邮箱"
- 所有发往 200 个邮箱的邮件，自动转发到用户设定的目标邮箱

---

## 二、方案对比

| 方案 | 原理 | 优点 | 缺点 | 推荐度 |
|------|------|------|------|--------|
| Cloudflare Email Routing + Worker + KV | Worker 查 KV 动态路由 | 免费、无需 VPS | 整域名最多 200 个地址（硬限制），一个用户就用完 | ❌ 不适用 |
| **自建 SMTP 服务器（VPS）** | MX 记录指向 VPS，自建服务收信后查数据库转发 | 无地址数量限制，完全自控 | 需要 VPS，需配置 MX | ✅ 推荐 |
| ImprovMX / ForwardEmail API | 调第三方 API 管理转发规则 | 无需运维 | 费用高，依赖第三方 | ⭐⭐ |

**结论：选方案二，用 VPS 自建 SMTP 转发服务。**

---

## 三、整体架构

```
发件人
  │
  │  发送邮件到 abc123@flapysun.com
  ▼
Cloudflare DNS
  │  MX 记录 → mail.flapysun.com → VPS IP
  ▼
VPS（Google Cloud / CentOS 10）
  │
  ├─ [SMTP 接收容器]  监听 :25
  │     │
  │     │  查询数据库：abc123 → user@gmail.com
  │     ▼
  │   SQLite 数据库
  │     │
  │     │  找到转发目标
  │     ▼
  │  [外发 SMTP]  Gmail / SendGrid / Mailgun
  │
  └─ [API 容器]  监听 :5000（Nginx 反代 :80）
        │
        ├─ 管理接口（商城后台调用，API Key 鉴权）
        └─ 用户设置页面（用 order_id 鉴权）
```

---

## 四、DNS 配置（Cloudflare）

在 Cloudflare 控制台添加以下两条记录：

| 类型 | 名称 | 内容 | 代理状态 |
|------|------|------|----------|
| A  | `mail.flapysun.com` | VPS 的 IP 地址 | 关闭（灰云） |
| MX | `flapysun.com` | `mail.flapysun.com`，优先级 10 | — |

> ⚠️ A 记录必须关闭 Cloudflare 代理（灰云），否则 SMTP 流量会被拦截。

---

## 五、项目结构

```
email-forwarder/
├── deploy.sh              ← 一键部署脚本（CentOS 10）
├── docker-compose.yml     ← 编排三个容器
├── .env                   ← 环境变量配置
├── app/
│   ├── smtp_server.py     ← SMTP 接收 + 转发服务
│   ├── api.py             ← 管理 API + 用户前台页面
│   ├── models.py          ← 数据库模型（EmailRoute / ForwardLog）
│   ├── Dockerfile
│   ├── entrypoint.sh      ← 根据 SERVICE 变量启动不同服务
│   └── requirements.txt
└── nginx/
    └── default.conf       ← 反向代理到 api:5000
```

---

## 六、Docker 容器编排

系统由三个容器组成，共享一个 SQLite 数据卷：

```
┌─────────────────────────────────────────────────────┐
│                  docker-compose                      │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  smtp        │  │  api         │  │  nginx    │  │
│  │  :25         │  │  :5000       │  │  :80      │  │
│  │  接收转发邮件 │  │  管理+前台   │  │  反向代理  │  │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘  │
│         │                 │                │        │
│         └────────┬────────┘                │        │
│              db_data                       │        │
│              (SQLite)            外部请求 ←─┘        │
└─────────────────────────────────────────────────────┘
```

---

## 七、数据库设计

### EmailRoute 表（路由规则）

| 字段 | 类型 | 说明 |
|------|------|------|
| `local_part` | String PK | 邮箱前缀，如 `abc123` |
| `forward_to` | String | 用户设置的目标邮箱 |
| `active` | Boolean | 是否激活（设置转发后为 true） |
| `order_id` | String | 订单 ID（用于用户身份校验） |
| `buyer_name` | String | 买家名称 |
| `assigned_at` | DateTime | 分配时间 |
| `updated_at` | DateTime | 最后更新时间 |

### ForwardLog 表（转发日志）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String PK | UUID |
| `local_part` | String | 收件邮箱前缀 |
| `from_addr` | String | 原始发件人 |
| `forward_to` | String | 转发目标 |
| `subject` | Text | 邮件主题 |
| `status` | String | `success` / `failed` / `no_route` |
| `error` | Text | 失败原因（可空） |
| `created_at` | DateTime | 记录时间 |

---

## 八、核心业务流程

### 8.1 用户购买流程

```
用户下单
   │
   ▼
商城后台从邮箱池取一个空闲 local_part
   │
   ▼
POST /api/email/assign          ← 调用管理 API 分配邮箱
{
  "local_part": "abc123",
  "order_id":   "ORDER_001",
  "buyer_name": "张三"
}
   │
   ▼
数据库写入（active=false，forward_to=null）
   │
   ▼
给用户发送设置链接：
http://YOUR_VPS/setup?e=abc123&o=ORDER_001
```

### 8.2 用户设置转发流程

```
用户打开设置页面（/setup?e=abc123&o=ORDER_001）
   │
   ▼
输入自己的邮箱，如 user@gmail.com
   │
   ▼
POST /api/email/set-forward
{
  "local_part": "abc123",
  "order_id":   "ORDER_001",
  "forward_to": "user@gmail.com"
}
   │
   ▼
数据库更新（active=true，forward_to=user@gmail.com）
   │
   ▼
设置完成 ✓
```

### 8.3 邮件转发流程

```
有人发邮件到 abc123@flapysun.com
   │
   ▼
VPS 上的 SMTP 服务（端口 25）接收
   │
   ▼
提取 local_part = "abc123"
   │
   ▼
查询数据库：active=true AND local_part="abc123"
   │
   ├─ 找到 → forward_to = "user@gmail.com"
   │              │
   │              ▼
   │         构造转发邮件（保留原始内容、附件）
   │         添加 X-Original-To / X-Forwarded-From 头
   │              │
   │              ▼
   │         通过外发 SMTP 发出 → user@gmail.com ✓
   │         写入日志：status=success
   │
   └─ 未找到 → 写入日志：status=no_route，丢弃
```

### 8.4 订单到期流程

```
订单到期 / 退款
   │
   ▼
POST /api/email/release
{ "local_part": "abc123" }
   │
   ▼
数据库删除该记录
   │
   ▼
local_part 回到邮箱池，可重新分配
```

---

## 九、API 接口文档

所有管理接口需携带请求头：`X-API-Key: YOUR_KEY`

### 管理接口

#### 分配邮箱
```http
POST /api/email/assign
Content-Type: application/json
X-API-Key: YOUR_KEY

{
  "local_part": "abc123",
  "order_id":   "ORDER_001",
  "buyer_name": "张三"
}
```

#### 释放邮箱
```http
POST /api/email/release
Content-Type: application/json
X-API-Key: YOUR_KEY

{ "local_part": "abc123" }
```

#### 列出所有路由
```http
GET /api/email/list
X-API-Key: YOUR_KEY
```

#### 查看转发日志（最近 200 条）
```http
GET /api/email/logs
X-API-Key: YOUR_KEY
```

### 用户接口（用 order_id 鉴权，无需 API Key）

#### 设置 / 修改转发邮箱
```http
POST /api/email/set-forward
Content-Type: application/json

{
  "local_part": "abc123",
  "order_id":   "ORDER_001",
  "forward_to": "user@gmail.com"
}
```

#### 查询当前设置
```http
GET /api/email/info?local_part=abc123&order_id=ORDER_001
```

#### 用户设置页面
```
GET /setup?e=abc123&o=ORDER_001
```

---

## 十、环境变量说明

| 变量 | 说明 | 示例 |
|------|------|------|
| `MY_DOMAIN` | 你的邮箱域名 | `flapysun.com` |
| `SMTP_OUT_HOST` | 外发 SMTP 服务器 | `smtp.gmail.com` |
| `SMTP_OUT_PORT` | 外发 SMTP 端口 | `587` |
| `SMTP_OUT_USER` | 外发 SMTP 用户名 | `your@gmail.com` |
| `SMTP_OUT_PASS` | 外发 SMTP 密码 | Gmail 应用专用密码 |
| `SMTP_OUT_FROM` | 转发时的发件人地址 | `forward@flapysun.com` |
| `API_KEY` | 管理接口鉴权密钥 | 随机 32 位字符串 |
| `DATABASE_URL` | 数据库连接串 | `sqlite:////app/data/email_routes.db` |

---

## 十一、部署步骤

### 前置条件

- Google Cloud VPS，CentOS 10，至少 1 核 1G
- 已在 Google Cloud 控制台开放 TCP 25、TCP 80 入站规则
- 域名已托管到 Cloudflare

### 部署命令

```bash
# 1. 将项目上传到 VPS
scp email-forwarder.zip root@YOUR_VPS_IP:/tmp/

# 2. SSH 登录
ssh root@YOUR_VPS_IP

# 3. 解压并执行一键部署
cd /tmp
unzip email-forwarder.zip
cd email-forwarder
bash deploy.sh
```

脚本会自动完成：
1. 系统更新 & 安装基础依赖
2. 安装 Docker & Docker Compose
3. 配置 firewalld 开放端口
4. 生成 `.env` 配置文件
5. 构建镜像并启动三个容器
6. 打印 DNS 配置指引和 API 示例

---

## 十二、常用运维命令

```bash
cd /opt/email-forwarder

# 查看容器状态
docker compose ps

# 实时查看全部日志
docker compose logs -f

# 只看 SMTP 转发日志
docker compose logs -f smtp

# 只看 API 日志
docker compose logs -f api

# 重启所有服务
docker compose restart

# 停止
docker compose down

# 更新并重新部署
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## 十三、注意事项

1. **Google Cloud 25 端口**：GCP 部分新账号默认封锁 25 端口出站，需提交工单申请解封，或改用 2525/587 端口通过中继收信。

2. **Gmail 外发限制**：Gmail 每天免费发送上限约 500 封，邮件量大时建议改用 SendGrid / Mailgun（均有免费额度）。

3. **SPF / DKIM 配置**：为避免转发邮件被标记为垃圾邮件，建议在 Cloudflare 为 `flapysun.com` 配置 SPF 记录：
   ```
   TXT @ "v=spf1 ip4:YOUR_VPS_IP include:_spf.google.com ~all"
   ```

4. **数据备份**：SQLite 数据库存储在 Docker Volume `db_data` 中，建议定期备份：
   ```bash
   docker run --rm -v email-forwarder_db_data:/data \
     -v $(pwd):/backup alpine \
     tar czf /backup/db_backup_$(date +%Y%m%d).tar.gz /data
   ```

5. **安全建议**：API Key 请使用强随机字符串，不要对外暴露 `/api/email/list` 等管理接口，可在 Nginx 层加 IP 白名单。

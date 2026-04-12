# 邮件转发商城系统

一套基于 Docker 的邮件自动转发系统，支持将 @flapysun.com 的邮件动态转发到用户自定义邮箱。

## 架构

```
发件人 → *@flapysun.com (MX→VPS)
                ↓
        [SMTP 接收容器]  监听 :25
                ↓
        查询 SQLite 数据库
                ↓
        [外发 SMTP] Gmail/SendGrid
                ↓
        用户自定义邮箱 ✓
```

## 一键部署

```bash
# 1. 上传项目到 VPS
scp -r email-forwarder/ root@YOUR_VPS:/tmp/

# 2. SSH 进入 VPS
ssh root@YOUR_VPS

# 3. 执行部署脚本
cd /tmp/email-forwarder
bash deploy.sh
```

## DNS 配置（Cloudflare）

| 类型 | 名称              | 内容                | 代理 |
|------|-------------------|---------------------|------|
| MX   | flapysun.com      | mail.flapysun.com   | —    |
| A    | mail.flapysun.com | 你的 VPS IP         | 关闭 |

## API 文档

所有管理接口需要 Header: `X-API-Key: YOUR_KEY`

### 分配邮箱
```bash
POST /api/email/assign
{
  "local_part": "abc123",
  "order_id": "ORDER_001",
  "buyer_name": "张三"
}
```

### 用户设置转发（无需 API Key，用 order_id 鉴权）
```bash
POST /api/email/set-forward
{
  "local_part": "abc123",
  "order_id":   "ORDER_001",
  "forward_to": "user@gmail.com"
}
```

### 释放邮箱
```bash
POST /api/email/release
{ "local_part": "abc123" }
```

### 查看日志
```bash
GET /api/email/logs
GET /api/email/list
```

### 用户设置页面
```
http://YOUR_VPS/setup?e=abc123&o=ORDER_001
```

## 运维命令

```bash
cd /opt/email-forwarder

# 查看所有容器状态
docker compose ps

# 实时查看日志
docker compose logs -f

# 只看 SMTP 日志
docker compose logs -f smtp

# 重启
docker compose restart

# 停止
docker compose down
```

## 商城对接示例

```javascript
// 用户购买后，调用分配接口
await fetch('http://YOUR_VPS/api/email/assign', {
  method: 'POST',
  headers: {
    'X-API-Key': 'YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    local_part: 'abc123',       // 从你的邮箱池中取一个
    order_id:   'ORDER_001',
    buyer_name: '张三'
  })
});

// 给用户发送设置链接
const setupUrl = `http://YOUR_VPS/setup?e=abc123&o=ORDER_001`;
// 将 setupUrl 发送给用户
```

# SPF / DKIM / DMARC 配置 + AWS SES 接入文档

> 本文档解决两个问题：
> 1. 配置域名邮件认证（SPF/DKIM/DMARC），让转发的邮件不进垃圾箱
> 2. 接入 AWS SES 替换 Gmail，突破每日发送量限制

---

## 一、为什么必须配置这三项

邮件服务器收到一封来自 `forward@flapysun.com` 的邮件时，会做三件事：

```
收件方服务器检查流程
        │
        ├─ SPF 检查：发这封邮件的服务器 IP，是 flapysun.com 授权的吗？
        │
        ├─ DKIM 检查：邮件内容有没有被篡改？签名对得上吗？
        │
        └─ DMARC 检查：SPF 和 DKIM 都失败了怎么处理？拒绝/隔离/放行？
```

三项都配好，邮件正常投递进收件箱。
任何一项缺失，大概率进垃圾箱，严重时直接拒收。

---

## 二、SPF 配置

### 原理

SPF（Sender Policy Framework）是一条 DNS TXT 记录，声明"哪些 IP/服务器有权代表我的域名发邮件"。

### 配置步骤

在 Cloudflare DNS 中添加一条 TXT 记录：

| 类型 | 名称 | 内容 |
|------|------|------|
| TXT | `@`（即 flapysun.com） | 见下方 |

**内容根据你使用的外发服务填写：**

```
# 只用 AWS SES（推荐）
v=spf1 include:amazonses.com ~all

# 同时用 SES + 你的 VPS IP（VPS 直接发信时）
v=spf1 ip4:YOUR_VPS_IP include:amazonses.com ~all

# 过渡期：SES + Gmail 都用
v=spf1 include:amazonses.com include:_spf.google.com ~all
```

**参数说明：**
- `include:amazonses.com`：授权 AWS SES 的服务器发信
- `ip4:YOUR_VPS_IP`：授权你的 VPS 直接发信
- `~all`：其他来源"软失败"（进垃圾箱但不拒绝），生产环境稳定后可改为 `-all`（硬拒绝）

### 验证 SPF

```bash
# 查询 SPF 记录是否生效（DNS 传播需要几分钟到几小时）
dig TXT flapysun.com +short

# 或用在线工具
# https://mxtoolbox.com/spf.aspx
```

---

## 三、DKIM 配置

### 原理

DKIM（DomainKeys Identified Mail）用非对称加密对邮件签名：
- **私钥**：在发信服务器上，发邮件时对邮件内容签名
- **公钥**：放在 DNS TXT 记录中，收件方用来验证签名

AWS SES 会帮你生成密钥对并提供 DNS 记录，你只需要在 Cloudflare 里添加即可。

### 步骤（AWS SES 托管 DKIM，最简单）

**1. 登录 AWS 控制台 → SES → Verified Identities → Create Identity**

选择 "Domain"，输入 `flapysun.com`，勾选 "Easy DKIM"，选择 RSA_2048。

**2. AWS 会给你 3 条 CNAME 记录，类似这样：**

```
xxxxxxxxxxxx._domainkey.flapysun.com  →  xxxxxxxxxxxx.dkim.amazonses.com
yyyyyyyyyyyy._domainkey.flapysun.com  →  yyyyyyyyyyyy.dkim.amazonses.com
zzzzzzzzzzzz._domainkey.flapysun.com  →  zzzzzzzzzzzz.dkim.amazonses.com
```

**3. 在 Cloudflare 添加这 3 条 CNAME 记录（关闭代理，灰云）**

| 类型 | 名称 | 内容 | 代理 |
|------|------|------|------|
| CNAME | `xxxxxxxxxxxx._domainkey` | `xxxxxxxxxxxx.dkim.amazonses.com` | 关闭 |
| CNAME | `yyyyyyyyyyyy._domainkey` | `yyyyyyyyyyyy.dkim.amazonses.com` | 关闭 |
| CNAME | `zzzzzzzzzzzz._domainkey` | `zzzzzzzzzzzz.dkim.amazonses.com` | 关闭 |

**4. 等待 AWS 控制台显示 "DKIM status: Verified"（通常 5-30 分钟）**

### 验证 DKIM

```bash
# 替换 xxxxxxxxxxxx 为你的实际值
dig CNAME xxxxxxxxxxxx._domainkey.flapysun.com +short
```

---

## 四、DMARC 配置

### 原理

DMARC 告诉收件方：当 SPF 和 DKIM 都验证失败时，应该怎么处理这封邮件，以及把结果报告发到哪里。

### 配置步骤

在 Cloudflare 添加一条 TXT 记录：

| 类型 | 名称 | 内容 |
|------|------|------|
| TXT | `_dmarc` | 见下方 |

**分阶段配置（推荐循序渐进）：**

```bash
# 第一阶段：只监控，不拦截（刚上线时用，观察报告）
v=DMARC1; p=none; rua=mailto:dmarc-report@flapysun.com

# 第二阶段：软隔离（稳定运行 1-2 周后）
v=DMARC1; p=quarantine; pct=50; rua=mailto:dmarc-report@flapysun.com

# 第三阶段：严格拒绝（完全确认没问题后）
v=DMARC1; p=reject; rua=mailto:dmarc-report@flapysun.com
```

**参数说明：**
- `p=none/quarantine/reject`：失败时放行/隔离/拒绝
- `pct=50`：只对 50% 的邮件执行策略（灰度测试）
- `rua=`：DMARC 报告发送地址（可以是任意你能收到的邮箱）

---

## 五、邮件转发的特殊问题：ARC

### 问题背景

你的系统是**转发**而不是**原始发送**，这会导致一个特殊问题：

```
原始链路：sender@gmail.com → abc123@flapysun.com
转发链路：forward@flapysun.com → user@qq.com
```

当你把邮件转发出去时：
- 邮件的 `From` 头仍然是 `sender@gmail.com`
- 但实际发出邮件的服务器是你的 VPS / AWS SES
- 收件方做 SPF 检查时，发现这个 IP 不在 `gmail.com` 的 SPF 白名单里 → **SPF 失败**

### 解决方案

**方案 A（最简单）：改写 From 头**

把转发邮件的 `From` 改为你自己域名的地址：

```python
# smtp_server.py 中修改 forward_email() 函数
fwd["From"]    = f"forward@{MY_DOMAIN}"      # 改为你的域名
fwd["Reply-To"] = from_hdr                    # 保留原始发件人，方便回复
```

这样 SPF 检查的是 `flapysun.com`，就能通过了。
缺点：用户看到的发件人是 `forward@flapysun.com` 而不是原始发件人（但 Reply-To 保留，回复时仍然回到原始发件人）。

**方案 B（更完善）：添加 ARC 签名**

ARC（Authenticated Received Chain）是专为邮件转发设计的协议，告诉收件方"这封邮件经过了合法的转发"。

安装库：
```bash
pip install arc-message
```

在 `smtp_server.py` 的 `forward_email()` 中添加 ARC 签名：

```python
# 这部分较复杂，如果方案 A 够用就不必实现
# 主要转发场景下方案 A 已经满足需求
```

**推荐：先用方案 A，观察投递率，有问题再研究 ARC。**

---

## 六、AWS SES 接入

### 6.1 注册与配置

**1. 注册 AWS 账号**
访问 https://aws.amazon.com，注册时需要信用卡（验证身份，不会扣费）。

**2. 开通 SES**
AWS 控制台 → 搜索 "SES" → 选择离你最近的区域（推荐 `ap-northeast-1` 东京 或 `us-east-1` 弗吉尼亚）

**3. 验证域名**
按第三节（DKIM 配置）的步骤在 SES 中验证 `flapysun.com`。

**4. 申请解除沙盒限制（重要！）**

SES 默认处于"沙盒模式"，只能发给你验证过的邮箱地址，不能给任意用户发信。

申请步骤：
```
SES 控制台 → Account dashboard → Request production access

填写：
  Mail Type: Transactional（事务性邮件）
  Website URL: http://YOUR_VPS（或者你的商城域名）
  Use case description:
    "We operate an email forwarding service. Users purchase a
     forwarding mailbox and receive transactional emails containing
     their setup link. All recipients have opted in by purchasing
     our service."
  Additional contacts: 你的邮箱
```

通常 **24 小时内**审核通过，通过后每天可发 **62,000 封**（在 EC2/其他 AWS 服务器上免费，GCP 上 $0.10/1000 封）。

### 6.2 创建 SMTP 凭证

```
SES 控制台 → SMTP settings → Create SMTP credentials
```

会生成一对 SMTP 用户名/密码（不是你的 AWS 账号密码），记录下来。

SMTP 服务器地址（以东京区域为例）：
```
Host: email-smtp.ap-northeast-1.amazonaws.com
Port: 587（STARTTLS）或 465（SSL）
```

### 6.3 修改 .env（唯一需要改的地方）

```bash
# 删除或注释掉 Gmail 配置
# SMTP_OUT_HOST=smtp.gmail.com
# SMTP_OUT_PORT=587
# SMTP_OUT_USER=your_gmail@gmail.com
# SMTP_OUT_PASS=your_app_password

# 替换为 AWS SES
SMTP_OUT_HOST=email-smtp.ap-northeast-1.amazonaws.com
SMTP_OUT_PORT=587
SMTP_OUT_USER=AKIAIOSFODNN7EXAMPLE        # SES SMTP 用户名
SMTP_OUT_PASS=BmFtcGxlU0VTU01UUFBBU1MK  # SES SMTP 密码
SMTP_OUT_FROM=forward@flapysun.com
```

**重启容器使配置生效：**

```bash
cd /opt/email-forwarder
docker compose restart smtp
```

就这一步，代码零修改。

### 6.4 验证 SES 发信

```bash
# 在 VPS 上测试 SES SMTP 连通性
python3 - <<'PYEOF'
import smtplib

host = "email-smtp.ap-northeast-1.amazonaws.com"
user = "YOUR_SES_SMTP_USER"
pwd  = "YOUR_SES_SMTP_PASS"

with smtplib.SMTP(host, 587) as s:
    s.starttls()
    s.login(user, pwd)
    print("SES SMTP 连接成功！")
PYEOF
```

---

## 七、DNS 记录汇总

配置完成后，`flapysun.com` 的 DNS 应包含以下记录：

| 类型 | 名称 | 内容 | 代理 |
|------|------|------|------|
| A | `mail` | VPS IP | 关闭 |
| MX | `@` | `mail.flapysun.com`（优先级 10） | — |
| TXT | `@` | `v=spf1 include:amazonses.com ~all` | — |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc-report@flapysun.com` | — |
| CNAME | `xxxxxx._domainkey` | `xxxxxx.dkim.amazonses.com` | 关闭 |
| CNAME | `yyyyyy._domainkey` | `yyyyyy.dkim.amazonses.com` | 关闭 |
| CNAME | `zzzzzz._domainkey` | `zzzzzz.dkim.amazonses.com` | 关闭 |

---

## 八、一键检测脚本

将此脚本上传到 VPS，可随时运行检查配置状态：

```bash
#!/bin/bash
# check_email_config.sh
DOMAIN="flapysun.com"
echo "════════════════════════════════════"
echo "  邮件配置检测：$DOMAIN"
echo "════════════════════════════════════"

echo ""
echo "【MX 记录】"
dig MX $DOMAIN +short

echo ""
echo "【SPF 记录】"
dig TXT $DOMAIN +short | grep spf

echo ""
echo "【DMARC 记录】"
dig TXT _dmarc.$DOMAIN +short

echo ""
echo "【DKIM 记录（需替换为你的实际前缀）】"
# dig CNAME xxxxxx._domainkey.$DOMAIN +short

echo ""
echo "【SMTP 连通性测试】"
python3 -c "
import smtplib, os
host = os.environ.get('SMTP_OUT_HOST','')
user = os.environ.get('SMTP_OUT_USER','')
pwd  = os.environ.get('SMTP_OUT_PASS','')
if not host:
    print('未设置 SMTP 环境变量，跳过')
else:
    try:
        with smtplib.SMTP(host, 587, timeout=10) as s:
            s.starttls()
            s.login(user, pwd)
            print(f'SMTP 连接成功：{host}')
    except Exception as e:
        print(f'SMTP 连接失败：{e}')
"
echo ""
echo "在线检测工具："
echo "  SPF:   https://mxtoolbox.com/spf.aspx"
echo "  DKIM:  https://mxtoolbox.com/dkim.aspx"
echo "  DMARC: https://mxtoolbox.com/dmarc.aspx"
echo "  综合:  https://mail-tester.com"
```

```bash
chmod +x check_email_config.sh
bash check_email_config.sh
```

---

## 九、投递率优化建议

按优先级排序：

1. **配置 SPF + DKIM**（必须，本文档已覆盖）
2. **From 头改为你自己域名**（必须，见第五节方案 A）
3. **申请 SES 生产访问**（必须，否则只能发给验证邮箱）
4. **DMARC 从 none 逐步收紧**（建议，运行 2 周后改为 quarantine）
5. **发送量缓慢增长**（建议，新 IP/域名突然大量发信会触发反垃圾机制）
6. **监控退信率**（SES 控制台有 Bounce/Complaint 统计，超过 5% 要排查）
7. **用 mail-tester.com 测试得分**（发一封测试邮件，目标 10/10 分）


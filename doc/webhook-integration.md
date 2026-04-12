# 第一阶段：Webhook 对接文档

> 适用平台：Lemon Squeezy / WooCommerce / 彩虹易支付
> 目标：用户支付成功后，平台回调你的转发引擎，自动分配邮箱并给用户发设置链接

---

## 一、对接原理

```
用户在平台下单支付
       │
       ▼
平台触发 Webhook（POST 请求）
       │
       ▼
你的 /webhook/order-paid 接口
       │
       ├─ 1. 验证签名（防伪造）
       ├─ 2. 从邮箱池取一个空闲 local_part
       ├─ 3. 调用 /api/email/assign 分配邮箱
       └─ 4. 发送邮件给用户，含设置链接
```

---

## 二、前置准备：邮箱池管理

在转发引擎数据库中预先写入 200 个空闲邮箱，作为"库存池"。

### 初始化脚本（在 VPS 上执行一次）

```python
# init_pool.py
# 将此文件放到 app/ 目录，执行：docker exec email-api python init_pool.py

from models import Session, EmailRoute

# 你的 200 个邮箱前缀列表
# 命名规则建议：随机字符串，避免被猜测
EMAIL_POOL = [
    "shop001", "shop002", "shop003",  # ... 一直到 shop200
    # 或者用随机字符串：
    # "x7k2m", "p9q4n", "r3w8j", ...
]

db = Session()
for local_part in EMAIL_POOL:
    existing = db.query(EmailRoute).filter_by(local_part=local_part).first()
    if not existing:
        db.add(EmailRoute(
            local_part=local_part,
            active=False,
            order_id=None,   # order_id 为 None 表示空闲
            buyer_name=None,
        ))
db.commit()
db.close()
print(f"初始化完成，共写入 {len(EMAIL_POOL)} 个邮箱")
```

### 取空闲邮箱的逻辑（在 webhook 接口中调用）

```python
def get_free_email():
    """从池中取一个未分配的邮箱，没有则返回 None"""
    db = Session()
    try:
        route = db.query(EmailRoute).filter_by(order_id=None).first()
        return route.local_part if route else None
    finally:
        db.close()
```

---

## 三、在 api.py 中新增 Webhook 接口

将以下代码追加到 `api.py`：

```python
import hmac
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── 环境变量（在 .env 中添加）──────────────────────────────────────────
WEBHOOK_SECRET_LS   = os.environ.get("WEBHOOK_SECRET_LS", "")    # Lemon Squeezy
WEBHOOK_SECRET_WC   = os.environ.get("WEBHOOK_SECRET_WC", "")    # WooCommerce
WEBHOOK_SECRET_CYHF = os.environ.get("WEBHOOK_SECRET_CYHF", "")  # 彩虹易支付


def get_free_local_part():
    """从邮箱池取一个空闲 local_part"""
    db = Session()
    try:
        route = db.query(EmailRoute).filter_by(order_id=None).first()
        return route.local_part if route else None
    finally:
        db.close()


def send_setup_email(to_email, local_part, order_id, buyer_name=""):
    """发送设置链接邮件给用户"""
    setup_url = f"http://{os.environ.get('VPS_HOST', 'YOUR_VPS_IP')}/setup?e={local_part}&o={order_id}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"【{MY_DOMAIN}】您的专属邮箱已就绪，请完成设置"
    msg["From"]    = os.environ.get("SMTP_OUT_FROM")
    msg["To"]      = to_email

    html = f"""
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:24px">
      <h2 style="color:#4A7EF5">您的邮件转发服务已开通</h2>
      <p>亲爱的 {buyer_name or '用户'}，感谢您的购买！</p>
      <p>您的专属邮箱地址为：</p>
      <p style="background:#F0F4FF;padding:12px 16px;border-radius:8px;
                font-size:18px;font-weight:bold;color:#3355CC">
        {local_part}@{MY_DOMAIN}
      </p>
      <p>请点击下方按钮设置您的转发邮箱（设置后所有邮件将自动转发到您填写的邮箱）：</p>
      <a href="{setup_url}"
         style="display:inline-block;background:#4A7EF5;color:#fff;
                text-decoration:none;padding:12px 24px;border-radius:8px;
                font-weight:500;margin:8px 0">
        点击设置转发邮箱 →
      </a>
      <p style="color:#888;font-size:13px;margin-top:24px">
        订单号：{order_id}<br>
        如有问题请回复本邮件
      </p>
    </div>
    """
    msg.attach(MIMEText(html, "html"))

    smtp_host = os.environ.get("SMTP_OUT_HOST")
    smtp_port = int(os.environ.get("SMTP_OUT_PORT", 587))
    smtp_user = os.environ.get("SMTP_OUT_USER")
    smtp_pass = os.environ.get("SMTP_OUT_PASS")

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(smtp_user, smtp_pass)
        smtp.sendmail(smtp_user, [to_email], msg.as_bytes())


def process_new_order(order_id, buyer_email, buyer_name=""):
    """
    核心发货逻辑（被各平台 Webhook 统一调用）
    返回 (success: bool, message: str)
    """
    # 1. 检查订单是否已处理（幂等）
    db = Session()
    try:
        existing = db.query(EmailRoute).filter_by(order_id=order_id).first()
        if existing:
            return True, f"订单已处理: {existing.local_part}@{MY_DOMAIN}"
    finally:
        db.close()

    # 2. 取空闲邮箱
    local_part = get_free_local_part()
    if not local_part:
        return False, "邮箱池已耗尽，请联系管理员"

    # 3. 分配邮箱
    db = Session()
    try:
        route = db.query(EmailRoute).filter_by(local_part=local_part).first()
        route.order_id   = order_id
        route.buyer_name = buyer_name
        route.active     = False
        db.commit()
    finally:
        db.close()

    # 4. 发送设置邮件
    try:
        send_setup_email(buyer_email, local_part, order_id, buyer_name)
    except Exception as e:
        app.logger.error(f"发送设置邮件失败: {e}")
        # 邮件发失败不影响分配，管理员可手动重发

    return True, f"发货成功: {local_part}@{MY_DOMAIN} → {buyer_email}"
```

---

## 四、Lemon Squeezy 对接

### 4.1 获取 Webhook Secret

Lemon Squeezy 控制台 → Settings → Webhooks → 创建 Webhook：
- URL：`http://YOUR_VPS/webhook/lemon-squeezy`
- Events：勾选 `order_created`
- 复制 Signing Secret

### 4.2 在 .env 中添加

```
WEBHOOK_SECRET_LS=your_lemon_squeezy_signing_secret
```

### 4.3 Webhook 接口代码

```python
@app.route("/webhook/lemon-squeezy", methods=["POST"])
def webhook_lemon_squeezy():
    # 1. 验证签名
    signature = request.headers.get("X-Signature", "")
    raw_body  = request.get_data()
    expected  = hmac.new(
        WEBHOOK_SECRET_LS.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return jsonify({"error": "invalid signature"}), 401

    # 2. 解析 payload
    data  = request.json
    event = data.get("meta", {}).get("event_name", "")

    if event != "order_created":
        return jsonify({"status": "ignored"}), 200

    order = data.get("data", {}).get("attributes", {})
    order_id    = str(data["data"]["id"])
    buyer_email = order.get("user_email", "")
    buyer_name  = order.get("user_name", "")

    # 3. 发货
    ok, msg = process_new_order(order_id, buyer_email, buyer_name)
    app.logger.info(f"[LS Webhook] {msg}")

    return jsonify({"success": ok, "message": msg}), 200 if ok else 500
```

### 4.3 Lemon Squeezy Payload 结构参考

```json
{
  "meta": { "event_name": "order_created" },
  "data": {
    "id": "123456",
    "attributes": {
      "user_email": "buyer@gmail.com",
      "user_name":  "张三",
      "status":     "paid",
      "total":      9900
    }
  }
}
```

---

## 五、WooCommerce 对接

### 5.1 安装插件

WooCommerce → 设置 → 高级 → Webhooks → 添加 Webhook：
- 主题：`订单已创建`（Order Created）
- 传送网址：`http://YOUR_VPS/webhook/woocommerce`
- 密钥：填写一个随机字符串，复制备用

### 5.2 在 .env 中添加

```
WEBHOOK_SECRET_WC=your_woocommerce_webhook_secret
```

### 5.3 Webhook 接口代码

```python
@app.route("/webhook/woocommerce", methods=["POST"])
def webhook_woocommerce():
    # 1. 验证签名（WooCommerce 用 HMAC-SHA256 Base64）
    import base64
    signature = request.headers.get("X-WC-Webhook-Signature", "")
    raw_body  = request.get_data()
    expected  = base64.b64encode(
        hmac.new(WEBHOOK_SECRET_WC.encode(), raw_body, hashlib.sha256).digest()
    ).decode()

    if not hmac.compare_digest(signature, expected):
        return jsonify({"error": "invalid signature"}), 401

    # 2. 解析 payload
    data   = request.json
    status = data.get("status", "")

    # 只处理已支付订单
    if status not in ("processing", "completed"):
        return jsonify({"status": "ignored"}), 200

    order_id    = str(data.get("id", ""))
    buyer_email = data.get("billing", {}).get("email", "")
    buyer_name  = (
        data.get("billing", {}).get("first_name", "") + " " +
        data.get("billing", {}).get("last_name", "")
    ).strip()

    ok, msg = process_new_order(order_id, buyer_email, buyer_name)
    app.logger.info(f"[WC Webhook] {msg}")

    return jsonify({"success": ok, "message": msg}), 200 if ok else 500
```

---

## 六、彩虹易支付对接

彩虹易支付回调是 GET 请求，签名用 MD5。

### 6.1 在 .env 中添加

```
WEBHOOK_SECRET_CYHF=your_rainbow_pay_key
```

### 6.2 Webhook 接口代码

```python
import hashlib

@app.route("/webhook/rainbow-pay", methods=["GET", "POST"])
def webhook_rainbow_pay():
    """
    彩虹易支付回调（GET 参数）
    参数：pid, type, out_trade_no, trade_no, name, money, trade_status, sign, sign_type
    """
    args = request.args if request.method == "GET" else request.form

    trade_status = args.get("trade_status", "")
    if trade_status != "TRADE_SUCCESS":
        return "success"   # 彩虹要求返回 "success" 字符串

    # 验证 MD5 签名
    sign      = args.get("sign", "")
    sign_type = args.get("sign_type", "MD5")

    # 按参数名 ASCII 排序，拼接键值对
    params = {k: v for k, v in args.items() if k not in ("sign", "sign_type")}
    sign_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sign_str += WEBHOOK_SECRET_CYHF
    expected = hashlib.md5(sign_str.encode()).hexdigest()

    if sign.lower() != expected.lower():
        return "fail"

    order_id    = args.get("out_trade_no", "")  # 你的商户订单号
    buyer_email = args.get("param", "")          # 下单时把邮箱放在 param 字段传过来
    buyer_name  = args.get("name", "")

    ok, msg = process_new_order(order_id, buyer_email, buyer_name)
    app.logger.info(f"[Rainbow Webhook] {msg}")

    return "success"   # 彩虹要求无论如何返回 success
```

> **彩虹易支付注意**：用户下单时需要在"备注/param 字段"要求用户填写接收设置链接的邮箱，因为彩虹回调不携带买家邮箱，需要商品页面引导用户在 param 字段填写。

---

## 七、.env 补充项

在原有 `.env` 末尾追加：

```
# Webhook 签名密钥
WEBHOOK_SECRET_LS=
WEBHOOK_SECRET_WC=
WEBHOOK_SECRET_CYHF=

# 用户收到的设置链接中的 HOST
VPS_HOST=your_vps_ip_or_domain
```

---

## 八、测试 Webhook

### 本地测试工具（curl 模拟回调）

```bash
# 测试彩虹易支付回调
curl "http://YOUR_VPS/webhook/rainbow-pay?\
pid=1001&type=alipay&out_trade_no=TEST001&trade_no=2024010100001\
&name=邮件转发服务&money=99.00&trade_status=TRADE_SUCCESS\
&param=buyer@gmail.com&sign=MD5签名&sign_type=MD5"

# 测试 Lemon Squeezy（跳过签名验证，仅用于开发环境）
curl -X POST http://YOUR_VPS/webhook/lemon-squeezy \
  -H "Content-Type: application/json" \
  -H "X-Signature: test" \
  -d '{
    "meta": {"event_name": "order_created"},
    "data": {
      "id": "TEST001",
      "attributes": {
        "user_email": "buyer@gmail.com",
        "user_name": "测试用户",
        "status": "paid"
      }
    }
  }'
```

### 验证发货结果

```bash
# 查看是否分配成功
curl http://YOUR_VPS/api/email/list \
  -H "X-API-Key: YOUR_KEY"

# 查看转发日志
curl http://YOUR_VPS/api/email/logs \
  -H "X-API-Key: YOUR_KEY"
```


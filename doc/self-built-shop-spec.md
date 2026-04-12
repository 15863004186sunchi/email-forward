# 第二阶段：自建购买系统设计文档

> 目标：将购买系统与邮件转发引擎合并为一个完整项目，统一部署，共享数据库。
> 技术栈：Python Flask + SQLite（可升级 MySQL）+ Docker Compose
> 支付：支付宝当面付 / 微信支付 Native（均支持个人/企业收款）

---

## 一、整体架构

```
                        ┌─────────────────────────────────────────┐
                        │           Docker Compose                 │
                        │                                          │
  用户浏览器             │  ┌──────────┐      ┌──────────────────┐ │
      │                 │  │  nginx   │      │   共享 SQLite     │ │
      │ :80/:443        │  │  :80     │      │   /app/data/      │ │
      └────────────────►│  └────┬─────┘      └────────┬─────────┘ │
                        │       │                      │           │
                        │  ┌────▼──────────────────────▼────────┐  │
                        │  │           shop 容器 :5000           │  │
                        │  │  商品展示 / 下单 / 支付 / 用户中心   │  │
                        │  └────────────────────────────────────┘  │
                        │                                          │
                        │  ┌─────────────────────────────────────┐ │
                        │  │           smtp 容器 :25              │ │
                        │  │      邮件接收 + 转发（已有）          │ │
                        │  └─────────────────────────────────────┘ │
                        └─────────────────────────────────────────┘
```

> **与第一阶段的核心区别**：不再需要 Webhook，购买逻辑直接在同一进程内调用
> `process_new_order()`，省掉了网络请求和签名验证。

---

## 二、数据库新增表

在原有 `EmailRoute` 和 `ForwardLog` 基础上新增 3 张表：

### 2.1 Product（商品表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer PK | 自增 |
| `name` | String | 商品名称，如"邮件转发服务" |
| `description` | Text | 商品描述（支持 HTML） |
| `price` | Integer | 价格（分），如 9900 = ¥99.00 |
| `duration_days` | Integer | 服务天数，0 = 永久 |
| `stock` | Integer | 库存（-1 = 无限） |
| `active` | Boolean | 是否上架 |
| `created_at` | DateTime | — |

### 2.2 Order（订单表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String PK | 商户订单号，如 `20240101120000001` |
| `product_id` | Integer FK | 关联商品 |
| `buyer_email` | String | 买家邮箱（用于接收设置链接） |
| `buyer_name` | String | 买家姓名（可选） |
| `amount` | Integer | 实付金额（分） |
| `status` | String | `pending` / `paid` / `delivered` / `expired` / `refunded` |
| `pay_type` | String | `alipay` / `wechat` |
| `trade_no` | String | 第三方支付流水号 |
| `local_part` | String | 分配的邮箱前缀（付款后填入） |
| `expire_at` | DateTime | 服务到期时间（null = 永久） |
| `created_at` | DateTime | 下单时间 |
| `paid_at` | DateTime | 支付时间 |

### 2.3 User（用户表，可选）

> 如果不做用户账号系统，可以用 `order_id + buyer_email` 验证身份，跳过此表。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | Integer PK | — |
| `email` | String UNIQUE | 用户邮箱（即登录账号） |
| `password_hash` | String | bcrypt 哈希 |
| `created_at` | DateTime | — |

---

## 三、页面与路由设计

### 3.1 用户侧页面

| 路由 | 页面 | 说明 |
|------|------|------|
| `GET /` | 首页/商品列表 | 展示商品，含购买按钮 |
| `GET /product/<id>` | 商品详情 | 价格、说明、购买入口 |
| `POST /order/create` | — | 创建订单，跳转支付页 |
| `GET /pay/<order_id>` | 支付页 | 展示二维码，轮询支付状态 |
| `GET /pay/<order_id>/status` | — | JSON 接口，返回支付状态 |
| `GET /order/<order_id>` | 订单详情 | 含设置链接入口 |
| `GET /setup` | 转发设置页 | 已有，`?e=xxx&o=yyy` |
| `GET /orders` | 我的订单 | 按邮箱查询历史订单 |

### 3.2 管理侧页面

| 路由 | 页面 | 说明 |
|------|------|------|
| `GET /admin` | 管理后台 | 已有，扩展订单管理 Tab |
| `GET /admin/orders` | 订单管理 | 查看/搜索所有订单 |
| `POST /admin/order/refund` | — | 手动退款/关闭订单 |
| `POST /admin/order/resend` | — | 重发设置邮件 |

### 3.3 支付回调路由

| 路由 | 说明 |
|------|------|
| `POST /pay/alipay/notify` | 支付宝异步通知 |
| `GET /pay/alipay/return` | 支付宝同步跳转 |
| `POST /pay/wechat/notify` | 微信支付回调 |

---

## 四、核心业务流程

### 4.1 下单支付流程

```
用户点击购买
     │
     ▼
POST /order/create
  body: { product_id, buyer_email, pay_type }
     │
     ├─ 生成订单号（时间戳+随机数）
     ├─ 写入 Order 表（status=pending）
     └─ 调用支付 SDK 生成二维码 URL
     │
     ▼
跳转 GET /pay/<order_id>
     │
     ├─ 展示支付二维码
     └─ 前端每 2 秒轮询 /pay/<order_id>/status
               │
               ▼ 用户扫码支付
               │
         支付平台异步回调 /pay/xxx/notify
               │
               ├─ 验证签名
               ├─ 更新 Order.status = paid
               ├─ 调用 process_new_order()
               │     ├─ 取空闲 local_part
               │     ├─ 更新 EmailRoute
               │     └─ 发送设置邮件给用户
               └─ 更新 Order.status = delivered
               │
               ▼
     前端轮询发现 status=delivered
               │
               ▼
     跳转 /order/<order_id>（展示成功 + 设置链接）
```

### 4.2 订单号生成规则

```python
import time, random, string

def generate_order_id():
    ts     = time.strftime("%Y%m%d%H%M%S")
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"{ts}{suffix}"   # 如 202401011200000001
```

### 4.3 支付状态轮询接口

```python
@app.route("/pay/<order_id>/status")
def pay_status(order_id):
    db = Session()
    try:
        order = db.query(Order).filter_by(id=order_id).first()
        if not order:
            return jsonify({"status": "not_found"})
        return jsonify({
            "status":     order.status,        # pending / paid / delivered
            "local_part": order.local_part,    # 分配成功后有值
        })
    finally:
        db.close()
```

前端轮询逻辑：

```javascript
async function pollStatus(orderId) {
  const timer = setInterval(async () => {
    const res  = await fetch(`/pay/${orderId}/status`);
    const data = await res.json();

    if (data.status === 'delivered') {
      clearInterval(timer);
      window.location.href = `/order/${orderId}`;   // 跳转到成功页
    } else if (data.status === 'expired') {
      clearInterval(timer);
      showError('订单已超时，请重新下单');
    }
  }, 2000);   // 每 2 秒查一次

  // 15 分钟超时
  setTimeout(() => clearInterval(timer), 15 * 60 * 1000);
}
```

---

## 五、支付集成

### 5.1 支付宝当面付（推荐个人使用）

**申请方式**：支付宝开放平台 → 创建应用 → 申请"当面付"权限（个人账号可申请）

**安装 SDK**：
```bash
pip install alipay-sdk-python
```

**生成二维码**：
```python
from alipay import AliPay

alipay = AliPay(
    appid=os.environ["ALIPAY_APP_ID"],
    app_notify_url=f"http://{VPS_HOST}/pay/alipay/notify",
    app_private_key_string=os.environ["ALIPAY_PRIVATE_KEY"],
    alipay_public_key_string=os.environ["ALIPAY_PUBLIC_KEY"],
)

def create_alipay_qr(order_id, amount_fen, subject):
    """返回支付宝二维码内容（前端用 qrcode.js 渲染）"""
    qr_content = alipay.api_alipay_trade_precreate(
        subject=subject,
        out_trade_no=order_id,
        total_amount=str(amount_fen / 100),   # 转为元
    )
    return qr_content.get("qr_code")   # 返回 URL，前端渲染成二维码图片
```

**回调处理**：
```python
@app.route("/pay/alipay/notify", methods=["POST"])
def alipay_notify():
    data          = request.form.to_dict()
    signature     = data.pop("sign", None)
    sign_type     = data.pop("sign_type", "RSA2")
    trade_status  = data.get("trade_status", "")
    out_trade_no  = data.get("out_trade_no", "")
    trade_no      = data.get("trade_no", "")

    # 验证签名
    if not alipay.verify(data, signature):
        return "fail"

    # 只处理支付成功
    if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        return "success"

    # 处理发货
    db = Session()
    try:
        order = db.query(Order).filter_by(id=out_trade_no).first()
        if not order or order.status != "pending":
            return "success"   # 已处理，幂等返回

        order.status   = "paid"
        order.trade_no = trade_no
        order.paid_at  = datetime.utcnow()
        db.commit()

        ok, msg = process_new_order(
            order_id=out_trade_no,
            buyer_email=order.buyer_email,
            buyer_name=order.buyer_name or ""
        )
        if ok:
            order.status = "delivered"
            db.commit()
    finally:
        db.close()

    return "success"   # 支付宝要求返回 "success"
```

### 5.2 微信支付 Native（扫码支付）

**申请方式**：微信商户平台 → 申请 Native 支付（需要营业执照，个人建议用支付宝）

**安装 SDK**：
```bash
pip install wechatpayv3
```

**生成二维码**：
```python
from wechatpayv3 import WeChatPay, WeChatPayType

wxpay = WeChatPay(
    wechatpay_type=WeChatPayType.NATIVE,
    mchid=os.environ["WECHAT_MCH_ID"],
    private_key=os.environ["WECHAT_PRIVATE_KEY"],
    cert_serial_no=os.environ["WECHAT_CERT_SERIAL"],
    apiv3_key=os.environ["WECHAT_API_V3_KEY"],
    appid=os.environ["WECHAT_APP_ID"],
    notify_url=f"http://{VPS_HOST}/pay/wechat/notify",
)

def create_wechat_qr(order_id, amount_fen, description):
    code, msg = wxpay.pay(
        description=description,
        out_trade_no=order_id,
        amount={"total": amount_fen},
        pay_type=WeChatPayType.NATIVE,
    )
    if code == 200:
        return msg.get("code_url")   # 返回 URL，前端渲染成二维码
    return None
```

**回调处理**：
```python
@app.route("/pay/wechat/notify", methods=["POST"])
def wechat_notify():
    headers  = {k: v for k, v in request.headers.items()}
    body     = request.data.decode("utf-8")
    result   = wxpay.callback(headers, body)

    if result and result.get("event_type") == "TRANSACTION.SUCCESS":
        resource     = result.get("resource", {})
        out_trade_no = resource.get("out_trade_no", "")
        trade_no     = resource.get("transaction_id", "")

        db = Session()
        try:
            order = db.query(Order).filter_by(id=out_trade_no).first()
            if order and order.status == "pending":
                order.status   = "paid"
                order.trade_no = trade_no
                order.paid_at  = datetime.utcnow()
                db.commit()

                ok, msg = process_new_order(
                    order_id=out_trade_no,
                    buyer_email=order.buyer_email,
                    buyer_name=order.buyer_name or ""
                )
                if ok:
                    order.status = "delivered"
                    db.commit()
        finally:
            db.close()

    return jsonify({"code": "SUCCESS", "message": "成功"})
```

---

## 六、.env 新增配置项

```
# ── 支付宝 ─────────────────────────────────────────────────────────
ALIPAY_APP_ID=your_alipay_app_id
ALIPAY_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
ALIPAY_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----

# ── 微信支付（可选）──────────────────────────────────────────────────
WECHAT_APP_ID=your_wechat_app_id
WECHAT_MCH_ID=your_mch_id
WECHAT_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----
WECHAT_CERT_SERIAL=your_cert_serial_no
WECHAT_API_V3_KEY=your_api_v3_key

# ── 站点 ────────────────────────────────────────────────────────────
VPS_HOST=your_domain_or_ip        # 用于生成回调 URL 和设置链接
ORDER_TIMEOUT_MINUTES=15          # 订单超时时间
```

---

## 七、Docker Compose 调整

将 `api` 服务改为 `shop`（合并购买+管理+转发设置页），其余容器不变：

```yaml
version: "3.9"

services:

  smtp:
    build: ./app
    container_name: email-smtp
    restart: always
    environment:
      SERVICE: smtp
      # ... 同原有配置
    ports:
      - "25:25"
    volumes:
      - db_data:/app/data
    networks:
      - internal

  shop:                          # 原来的 api 容器，现在包含购买系统
    build: ./app
    container_name: email-shop
    restart: always
    environment:
      SERVICE: shop              # entrypoint.sh 新增 shop 分支
      MY_DOMAIN:    ${MY_DOMAIN}
      API_KEY:      ${API_KEY}
      VPS_HOST:     ${VPS_HOST}
      DATABASE_URL: sqlite:////app/data/email_routes.db
      ALIPAY_APP_ID:      ${ALIPAY_APP_ID}
      ALIPAY_PRIVATE_KEY: ${ALIPAY_PRIVATE_KEY}
      ALIPAY_PUBLIC_KEY:  ${ALIPAY_PUBLIC_KEY}
    volumes:
      - db_data:/app/data
    networks:
      - internal

  nginx:
    image: nginx:1.27-alpine
    container_name: email-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"               # HTTPS（配置证书后启用）
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro   # SSL 证书目录
    networks:
      - internal
    depends_on:
      - shop

volumes:
  db_data:

networks:
  internal:
    driver: bridge
```

`entrypoint.sh` 新增 `shop` 分支：

```bash
case "${SERVICE}" in
  smtp) exec python smtp_server.py ;;
  shop) exec gunicorn shop:app --bind 0.0.0.0:5000 --workers 2 --timeout 60 ;;
  *)    echo "SERVICE must be smtp or shop"; exit 1 ;;
esac
```

---

## 八、商品页面 UI 设计要求

### 首页（商品列表）

```
┌─────────────────────────────────────────────────────────┐
│  导航栏：Logo  商品  我的订单                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  📬  邮件转发服务                                │   │
│  │                                                 │   │
│  │  获得 200 个专属邮箱（@flapysun.com）            │   │
│  │  所有邮件自动转发到您指定的邮箱                   │   │
│  │                                                 │   │
│  │  ✓ 即时开通   ✓ 永久有效   ✓ 支持随时修改        │   │
│  │                                                 │   │
│  │  ¥99.00                    [立即购买]            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 支付页（/pay/<order_id>）

```
┌──────────────────────────────────────────┐
│  完成支付                                 │
│                                          │
│  订单号：202401011200000001               │
│  商品：邮件转发服务                        │
│  金额：¥99.00                            │
│                                          │
│  ┌──────────┐  ┌──────────┐             │
│  │ 支付宝   │  │ 微信支付  │  ← Tab 切换  │
│  └──────────┘  └──────────┘             │
│                                          │
│      ┌─────────────────┐                │
│      │                 │                │
│      │   二维码图片      │  ← qrcode.js  │
│      │                 │                │
│      └─────────────────┘                │
│                                          │
│  ⏱ 订单将在 14:32 后过期                 │
│  ● 等待支付中...（动画）                  │
└──────────────────────────────────────────┘
```

前端渲染二维码（引入 qrcode.js CDN）：
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>
  new QRCode(document.getElementById("qrcode"), {
    text: "{{ qr_url }}",   // 后端传入的支付 URL
    width: 200,
    height: 200,
  });
</script>
```

---

## 九、安全要点

1. **支付回调必须验签**：每个支付平台都有签名机制，务必验证，防止伪造回调
2. **幂等处理**：同一订单的回调可能触发多次，用 `order.status != "pending"` 判断跳过
3. **HTTPS**：上线后必须配置 SSL，否则支付宝/微信回调会失败
   ```bash
   # 用 certbot 申请免费证书（需要域名）
   docker run --rm -v ./nginx/certs:/etc/letsencrypt \
     certbot/certbot certonly --standalone -d your_domain.com
   ```
4. **订单超时关闭**：用定时任务每分钟扫描超时 pending 订单
   ```python
   # 在 shop.py 启动时启动后台线程
   import threading, time
   def close_expired_orders():
       while True:
           time.sleep(60)
           db = Session()
           cutoff = datetime.utcnow() - timedelta(minutes=ORDER_TIMEOUT)
           db.query(Order).filter(
               Order.status == "pending",
               Order.created_at < cutoff
           ).update({"status": "expired"})
           db.commit()
           db.close()
   threading.Thread(target=close_expired_orders, daemon=True).start()
   ```
5. **API Key 保护管理接口**：Nginx 层可加 IP 白名单限制 `/admin` 路径

---

## 十、两阶段迁移路径

```
第一阶段（现在）              第二阶段（稳定后）
─────────────────────         ──────────────────────────
外部平台（LS/WC）              自建 shop 容器
    │                              │
    │ Webhook 回调                 │ 直接函数调用
    ▼                              ▼
/webhook/xxx                  process_new_order()
    │                              │
    └──────────── 共用 ────────────┘
                    │
              EmailRoute 表
              ForwardLog 表
              邮件转发引擎
```

两个阶段共用同一个数据库和邮件转发引擎，**迁移时只需：**
1. 部署 `shop` 容器
2. 在外部平台停用 Webhook
3. 将商品链接从外部平台改为你自己的域名


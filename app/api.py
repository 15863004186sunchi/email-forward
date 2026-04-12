"""
商城管理 API + 用户设置前端 + 管理后台 + Webhook 接口
"""
import os
import re
import uuid
import hmac
import smtplib
import hashlib
import base64
from datetime import datetime
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, request, jsonify, render_template_string, abort
from models import Session, EmailRoute, ForwardLog, init_db
from admin_page import ADMIN_PAGE_HTML

app = Flask(__name__)
API_KEY              = os.environ.get("API_KEY", "change-me-secret")
MY_DOMAIN            = os.environ.get("MY_DOMAIN", "flapysun.com")
VPS_HOST             = os.environ.get("VPS_HOST", "")
WEBHOOK_SECRET_LS    = os.environ.get("WEBHOOK_SECRET_LS", "")
WEBHOOK_SECRET_WC    = os.environ.get("WEBHOOK_SECRET_WC", "")
WEBHOOK_SECRET_CYHF  = os.environ.get("WEBHOOK_SECRET_CYHF", "")
SMTP_OUT_HOST        = os.environ.get("SMTP_OUT_HOST", "")
SMTP_OUT_PORT        = int(os.environ.get("SMTP_OUT_PORT", "587"))
SMTP_OUT_USER        = os.environ.get("SMTP_OUT_USER", "")
SMTP_OUT_PASS        = os.environ.get("SMTP_OUT_PASS", "")
SMTP_OUT_FROM        = os.environ.get("SMTP_OUT_FROM", f"forward@{MY_DOMAIN}")


# ── 简单 API Key 鉴权 ─────────────────────────────────────────────────────
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if key != API_KEY:
            return jsonify({"success": False, "error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def valid_email(email):
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email or ""))


# ── 管理接口（需要 API Key）──────────────────────────────────────────────

@app.route("/api/email/assign", methods=["POST"])
@require_api_key
def assign():
    """分配邮箱给订单（用户购买后由商城后台调用）"""
    data       = request.json or {}
    local_part = (data.get("local_part") or "").strip().lower()
    order_id   = data.get("order_id", "")
    buyer_name = data.get("buyer_name", "")

    if not local_part:
        return jsonify({"success": False, "error": "local_part 必填"})

    db = Session()
    try:
        if db.query(EmailRoute).filter_by(local_part=local_part).first():
            return jsonify({"success": False, "error": "该邮箱已被占用"})
        db.add(EmailRoute(
            local_part=local_part,
            order_id=order_id,
            buyer_name=buyer_name,
        ))
        db.commit()
        return jsonify({"success": True, "email": f"{local_part}@{MY_DOMAIN}"})
    finally:
        db.close()


@app.route("/api/email/release", methods=["POST"])
@require_api_key
def release():
    """释放邮箱（订单到期/退款）"""
    local_part = (request.json or {}).get("local_part", "").strip().lower()
    db = Session()
    try:
        db.query(EmailRoute).filter_by(local_part=local_part).delete()
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


@app.route("/api/email/list", methods=["GET"])
@require_api_key
def list_routes():
    """列出所有路由"""
    db = Session()
    try:
        rows = db.query(EmailRoute).all()
        return jsonify({"success": True, "routes": [
            {
                "local_part": r.local_part,
                "email":      f"{r.local_part}@{MY_DOMAIN}",
                "forward_to": r.forward_to,
                "active":     r.active,
                "order_id":   r.order_id,
                "buyer_name": r.buyer_name,
            } for r in rows
        ]})
    finally:
        db.close()


@app.route("/api/email/logs", methods=["GET"])
@require_api_key
def logs():
    """查看转发日志（最近 200 条）"""
    db = Session()
    try:
        rows = db.query(ForwardLog).order_by(
            ForwardLog.created_at.desc()
        ).limit(200).all()
        return jsonify({"success": True, "logs": [
            {
                "local_part": r.local_part,
                "from_addr":  r.from_addr,
                "forward_to": r.forward_to,
                "subject":    r.subject,
                "status":     r.status,
                "error":      r.error,
                "time":       r.created_at.isoformat(),
            } for r in rows
        ]})
    finally:
        db.close()


# ── 用户设置接口（用 order_id 鉴权，无需 API Key）────────────────────────

@app.route("/api/email/set-forward", methods=["POST"])
def set_forward():
    """用户设置/修改转发邮箱"""
    data       = request.json or {}
    local_part = (data.get("local_part") or "").strip().lower()
    forward_to = (data.get("forward_to") or "").strip()
    order_id   = (data.get("order_id") or "").strip()

    if not valid_email(forward_to):
        return jsonify({"success": False, "error": "转发邮箱格式不正确"})

    db = Session()
    try:
        route = db.query(EmailRoute).filter_by(
            local_part=local_part, order_id=order_id
        ).first()
        if not route:
            return jsonify({"success": False, "error": "订单不存在或无权操作"})

        route.forward_to = forward_to
        route.active     = True
        route.updated_at = datetime.utcnow()
        db.commit()
        return jsonify({"success": True, "forward_to": forward_to})
    finally:
        db.close()


@app.route("/api/email/info", methods=["GET"])
def info():
    """用户查询自己的转发设置"""
    local_part = request.args.get("local_part", "").strip().lower()
    order_id   = request.args.get("order_id", "").strip()

    db = Session()
    try:
        route = db.query(EmailRoute).filter_by(
            local_part=local_part, order_id=order_id
        ).first()
        if not route:
            return jsonify({"exists": False})
        return jsonify({
            "exists":     True,
            "email":      f"{local_part}@{MY_DOMAIN}",
            "forward_to": route.forward_to,
            "active":     route.active,
        })
    finally:
        db.close()


# ── 用户前台页面 ──────────────────────────────────────────────────────────

USER_PAGE = \"\"\"
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>设置转发邮箱</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       background:#f5f5f5;min-height:100vh;display:flex;align-items:center;justify-content:center}
  .card{background:#fff;border-radius:12px;padding:32px 36px;width:100%;max-width:460px;
        box-shadow:0 2px 16px rgba(0,0,0,.08)}
  h2{font-size:20px;font-weight:600;margin-bottom:6px}
  .sub{color:#888;font-size:13px;margin-bottom:24px}
  label{display:block;font-size:13px;font-weight:500;color:#444;margin-bottom:6px}
  .email-box{background:#f0f4ff;border:1px solid #c7d7ff;border-radius:8px;
             padding:10px 14px;font-size:15px;font-weight:600;color:#3355cc;margin-bottom:20px}
  input[type=email]{width:100%;border:1px solid #ddd;border-radius:8px;
                    padding:10px 14px;font-size:14px;outline:none;transition:border .2s}
  input[type=email]:focus{border-color:#5b8af5}
  button{width:100%;background:#4a7ef5;color:#fff;border:none;border-radius:8px;
         padding:11px;font-size:15px;font-weight:500;cursor:pointer;margin-top:14px;transition:background .2s}
  button:hover{background:#3a6ee0}
  button:disabled{opacity:.6;cursor:not-allowed}
  .msg{margin-top:14px;font-size:13px;padding:10px 14px;border-radius:8px;display:none}
  .msg.ok{background:#e8f5e9;color:#2e7d32;display:block}
  .msg.err{background:#ffebee;color:#c62828;display:block}
  .hint{margin-top:20px;font-size:12px;color:#aaa;text-align:center}
</style>
</head>
<body>
<div class="card">
  <h2>设置转发邮箱</h2>
  <p class="sub">将您的专属邮箱收到的所有邮件转发到您自己的邮箱</p>
  <label>您的专属邮箱</label>
  <div class="email-box" id="myEmail">加载中...</div>
  <label for="fwd">转发到（您自己的邮箱）</label>
  <input type="email" id="fwd" placeholder="your@gmail.com">
  <button id="saveBtn" onclick="save()">保存设置</button>
  <div class="msg" id="msg"></div>
  <p class="hint">设置成功后约 1 分钟内生效，可随时修改</p>
</div>
<script>
  const p = new URLSearchParams(location.search);
  const localPart = p.get('e') || '';
  const orderId   = p.get('o') || '';

  const emailEl = document.getElementById('myEmail');
  if (!localPart || !orderId) {
    emailEl.textContent = '链接无效，请从订单页面重新进入';
    emailEl.style.color = '#c62828';
  } else {
    emailEl.textContent = localPart + '@{{ domain }}';
    fetch(`/api/email/info?local_part=${localPart}&order_id=${orderId}`)
      .then(r => r.json()).then(d => {
        if (d.exists && d.forward_to)
          document.getElementById('fwd').value = d.forward_to;
      });
  }

  async function save() {
    const fwd = document.getElementById('fwd').value.trim();
    const msg = document.getElementById('msg');
    const btn = document.getElementById('saveBtn');
    if (!fwd) { show(msg,'请输入转发邮箱','err'); return; }
    if (!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(fwd)) {
      show(msg,'邮箱格式不正确','err'); return;
    }
    btn.disabled = true; btn.textContent = '保存中...';
    const res = await fetch('/api/email/set-forward', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({local_part: localPart, forward_to: fwd, order_id: orderId})
    });
    const d = await res.json();
    btn.disabled = false; btn.textContent = '保存设置';
    if (d.success) {
      show(msg,'✓ 设置成功！邮件将转发到 ' + fwd,'ok');
      setTimeout(() => { msg.style.display='none'; }, 5000);
    } else {
      show(msg,'✗ ' + d.error,'err');
    }
  }

  function show(el, text, cls) {
    el.textContent = text;
    el.className = 'msg ' + cls;
  }
</script>
</body>
</html>
\"\"\"

@app.route("/setup")
def setup_page():
    return render_template_string(USER_PAGE, domain=MY_DOMAIN)


@app.route("/admin")
def admin_page():
    \"\"\"管理后台（API Key 由前端 JS 处理）\"\"\"
    return render_template_string(ADMIN_PAGE_HTML, domain=MY_DOMAIN)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "domain": MY_DOMAIN})


# ── Webhook 公共工具 ──────────────────────────────────────────────────────

def get_free_local_part():
    \"\"\"从邮箱池取一个空闲 local_part（order_id 为 None）\"\"\"
    db = Session()
    try:
        route = db.query(EmailRoute).filter_by(order_id=None).first()
        return route.local_part if route else None
    finally:
        db.close()


def send_setup_email(to_email, local_part, order_id, buyer_name=""):
    \"\"\"发送设置链接邮件给用户\"\"\"
    host = VPS_HOST or request.host
    setup_url = f"http://{host}/setup?e={local_part}&o={order_id}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"【{MY_DOMAIN}】您的专属邮箱已就绪，请完成设置"
    msg["From"]    = SMTP_OUT_FROM
    msg["To"]      = to_email

    html = f\"\"\"
    <div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:24px">
      <h2 style="color:#4A7EF5">您的邮件转发服务已开通</h2>
      <p>亲爱的 {buyer_name or '用户'}，感谢您的购买！</p>
      <p>您的专属邮箱地址为：</p>
      <p style="background:#F0F4FF;padding:12px 16px;border-radius:8px;
                font-size:18px;font-weight:bold;color:#3355CC">
        {local_part}@{MY_DOMAIN}
      </p>
      <p>请点击下方按钮设置您的转发邮箱：</p>
      <a href="{setup_url}"
         style="display:inline-block;background:#4A7EF5;color:#fff;
                text-decoration:none;padding:12px 24px;border-radius:8px;
                font-weight:500;margin:8px 0">
        点击设置转发邮箱 →
      </a>
      <p style="color:#888;font-size:13px;margin-top:24px">
        订单号：{order_id}<br>如有问题请回复本邮件
      </p>
    </div>
    \"\"\"
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_OUT_HOST, SMTP_OUT_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(SMTP_OUT_USER, SMTP_OUT_PASS)
        smtp.sendmail(SMTP_OUT_FROM, [to_email], msg.as_bytes())


def process_new_order(order_id, buyer_email, buyer_name=""):
    \"\"\"
    核心发货逻辑（被各平台 Webhook 统一调用，幂等）
    返回 (success: bool, message: str)
    \"\"\"
    # 1. 幂等：检查订单是否已处理
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

    # 4. 发送设置邮件（失败不影响分配，管理员可手动重发）
    try:
        send_setup_email(buyer_email, local_part, order_id, buyer_name)
    except Exception as e:
        app.logger.error(f"发送设置邮件失败: {e}")

    return True, f"发货成功: {local_part}@{MY_DOMAIN} → {buyer_email}"


# ── 重发设置邮件接口 ─────────────────────────────────────────────────────

@app.route("/api/email/resend", methods=["POST"])
@require_api_key
def resend_setup():
    \"\"\"重发设置链接邮件（管理员操作）\"\"\"
    data       = request.json or {}
    local_part = (data.get("local_part") or "").strip().lower()
    to_email   = (data.get("to_email") or "").strip()

    if not valid_email(to_email):
        return jsonify({"success": False, "error": "邮箱格式不正确"})

    db = Session()
    try:
        route = db.query(EmailRoute).filter_by(local_part=local_part).first()
        if not route or not route.order_id:
            return jsonify({"success": False, "error": "邮箱未分配"})
        try:
            send_setup_email(to_email, local_part, route.order_id, route.buyer_name or "")
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    finally:
        db.close()


# ── Webhook: Lemon Squeezy ───────────────────────────────────────────────

@app.route("/webhook/lemon-squeezy", methods=["POST"])
def webhook_lemon_squeezy():
    raw_body  = request.get_data()
    signature = request.headers.get("X-Signature", "")

    if WEBHOOK_SECRET_LS:
        expected = hmac.new(
            WEBHOOK_SECRET_LS.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return jsonify({"error": "invalid signature"}), 401

    data  = request.json or {}
    event = data.get("meta", {}).get("event_name", "")
    if event != "order_created":
        return jsonify({"status": "ignored"}), 200

    order       = data.get("data", {}).get("attributes", {})
    order_id    = str(data["data"]["id"])
    buyer_email = order.get("user_email", "")
    buyer_name  = order.get("user_name", "")

    ok, msg = process_new_order(order_id, buyer_email, buyer_name)
    app.logger.info(f"[LS Webhook] {msg}")
    return jsonify({"success": ok, "message": msg}), 200 if ok else 500


# ── Webhook: WooCommerce ─────────────────────────────────────────────────

@app.route("/webhook/woocommerce", methods=["POST"])
def webhook_woocommerce():
    raw_body  = request.get_data()
    signature = request.headers.get("X-WC-Webhook-Signature", "")

    if WEBHOOK_SECRET_WC:
        expected = base64.b64encode(
            hmac.new(WEBHOOK_SECRET_WC.encode(), raw_body, hashlib.sha256).digest()
        ).decode()
        if not hmac.compare_digest(signature, expected):
            return jsonify({"error": "invalid signature"}), 401

    data   = request.json or {}
    status = data.get("status", "")
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


# ── Webhook: 彩虹易支付 ──────────────────────────────────────────────────

@app.route("/webhook/rainbow-pay", methods=["GET", "POST"])
def webhook_rainbow_pay():
    args = request.args if request.method == "GET" else request.form

    trade_status = args.get("trade_status", "")
    if trade_status != "TRADE_SUCCESS":
        return "success"

    sign = args.get("sign", "")
    if WEBHOOK_SECRET_CYHF:
        params   = {k: v for k, v in args.items() if k not in ("sign", "sign_type")}
        sign_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        sign_str += WEBHOOK_SECRET_CYHF
        expected = hashlib.md5(sign_str.encode()).hexdigest()
        if sign.lower() != expected.lower():
            return "fail"

    order_id    = args.get("out_trade_no", "")
    buyer_email = args.get("param", "")   # 下单时把邮箱放在 param 字段
    buyer_name  = args.get("name", "")

    ok, msg = process_new_order(order_id, buyer_email, buyer_name)
    app.logger.info(f"[Rainbow Webhook] {msg}")
    return "success"


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)

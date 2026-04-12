"""
SMTP 接收 + 转发服务
监听 25 端口，收到邮件后查数据库，转发到用户自定义邮箱
"""
import asyncio
import smtplib
import logging
import os
import uuid
from datetime import datetime
from email import message_from_bytes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult, LoginPassword

from models import Session, EmailRoute, ForwardLog, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ── 配置（全部从环境变量读取）────────────────────────────────────────────
MY_DOMAIN     = os.environ.get("MY_DOMAIN", "flapysun.com")
SMTP_OUT_HOST = os.environ.get("SMTP_OUT_HOST", "smtp.gmail.com")
SMTP_OUT_PORT = int(os.environ.get("SMTP_OUT_PORT", "587"))
SMTP_OUT_USER = os.environ.get("SMTP_OUT_USER", "")
SMTP_OUT_PASS = os.environ.get("SMTP_OUT_PASS", "")
SMTP_OUT_FROM = os.environ.get("SMTP_OUT_FROM", f"forward@{MY_DOMAIN}")
LISTEN_PORT   = int(os.environ.get("SMTP_LISTEN_PORT", "25"))
# ─────────────────────────────────────────────────────────────────────────


def write_log(local_part, from_addr, forward_to, subject, status, error=None):
    db = Session()
    try:
        entry = ForwardLog(
            id=str(uuid.uuid4()),
            local_part=local_part,
            from_addr=from_addr,
            forward_to=forward_to or "",
            subject=subject or "",
            status=status,
            error=error,
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        log.error(f"写日志失败: {e}")
    finally:
        db.close()


def forward_email(original_msg, to_addr, forward_to, local_part):
    """用外发 SMTP 把原始邮件转发出去"""
    subject  = original_msg.get("Subject", "(无主题)")
    from_hdr = original_msg.get("From", "unknown")

    # 构造新邮件，保留原始内容
    fwd = MIMEMultipart("mixed")
    fwd["Subject"]          = f"[转发 {local_part}@{MY_DOMAIN}] {subject}"
    # 将原始发件人放入显示姓名，满足 Gmail 等中继站的要求，同时让用户看清来源
    fwd["From"]             = f'"{from_hdr}" <{SMTP_OUT_FROM}>'
    fwd["To"]               = forward_to
    fwd["Reply-To"]         = from_hdr
    fwd["X-Original-To"]    = to_addr
    fwd["X-Forwarded-From"] = from_hdr

    # 收集 text/plain 和 text/html
    body_plain = None
    body_html  = None
    attachments = []

    if original_msg.is_multipart():
        for part in original_msg.walk():
            ct   = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" in disp:
                attachments.append(part)
            elif ct == "text/plain" and body_plain is None:
                body_plain = part.get_payload(decode=True).decode("utf-8", errors="replace")
            elif ct == "text/html" and body_html is None:
                body_html  = part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        payload = original_msg.get_payload(decode=True)
        body_plain = payload.decode("utf-8", errors="replace") if payload else ""

    alt = MIMEMultipart("alternative")
    if body_plain:
        alt.attach(MIMEText(body_plain, "plain", "utf-8"))
    if body_html:
        alt.attach(MIMEText(body_html,  "html",  "utf-8"))
    fwd.attach(alt)

    for att in attachments:
        fwd.attach(att)

    with smtplib.SMTP(SMTP_OUT_HOST, SMTP_OUT_PORT, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(SMTP_OUT_USER, SMTP_OUT_PASS)
        smtp.sendmail(SMTP_OUT_FROM, [forward_to], fwd.as_bytes())

    return subject, from_hdr


class ForwardingHandler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """只接受发往本域名的邮件"""
        if not address.lower().endswith(f"@{MY_DOMAIN}"):
            return "550 不接受此邮件"
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        for rcpt in envelope.rcpt_tos:
            to_addr    = rcpt.lower().strip()
            local_part = to_addr.split("@")[0]

            log.info(f"收到邮件 → {to_addr}，来自 {envelope.mail_from}")

            db = Session()
            try:
                route = db.query(EmailRoute).filter_by(
                    local_part=local_part, active=True
                ).first()
                forward_to = route.forward_to if route else None
            finally:
                db.close()

            if not forward_to:
                log.warning(f"无转发规则: {local_part}")
                write_log(local_part, envelope.mail_from, None,
                          None, "no_route")
                continue

            try:
                msg = message_from_bytes(envelope.content)
                subject, from_hdr = forward_email(
                    msg, to_addr, forward_to, local_part
                )
                log.info(f"转发成功: {local_part} → {forward_to}")
                write_log(local_part, envelope.mail_from,
                          forward_to, subject, "success")
            except Exception as e:
                log.error(f"转发失败 {local_part} → {forward_to}: {e}")
                write_log(local_part, envelope.mail_from,
                          forward_to, None, "failed", str(e))

        return "250 Message accepted"


async def main():
    init_db()
    log.info(f"启动 SMTP 转发服务，域名={MY_DOMAIN}，端口={LISTEN_PORT}")
    controller = Controller(
        ForwardingHandler(),
        hostname="0.0.0.0",
        port=LISTEN_PORT,
    )
    controller.start()
    log.info("SMTP 服务已就绪，等待邮件...")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        controller.stop()
        log.info("SMTP 服务已停止")


if __name__ == "__main__":
    asyncio.run(main())

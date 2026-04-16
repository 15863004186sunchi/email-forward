import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

host = os.environ.get("SMTP_OUT_HOST")
port = int(os.environ.get("SMTP_OUT_PORT", 587))
user = os.environ.get("SMTP_OUT_USER")
pwd  = os.environ.get("SMTP_OUT_PASS")
from_addr = os.environ.get("SMTP_OUT_FROM")

print(f"Testing connection to {host}:{port} as {user}...")

try:
    with smtplib.SMTP(host, port, timeout=10) as s:
        s.set_debuglevel(1)
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(user, pwd)
        print("\n✅ SMTP Login Successful!")
except Exception as e:
    print(f"\n❌ SMTP Login Failed: {e}")

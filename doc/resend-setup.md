# Resend SMTP 配置说明

本项目目前使用 **Resend** 作为外发邮件服务，以替代 Gmail/AWS SES。

## 1. 核心配置 (.env)

```bash
SMTP_OUT_HOST=smtp.resend.com
SMTP_OUT_PORT=587
SMTP_OUT_USER=resend
SMTP_OUT_PASS=re_YOUR_RESEND_API_KEY  # 请在此处填入您的 API Key
SMTP_OUT_FROM=forward@flapysun.com
```

## 2. 维护建议

1.  **额度监控**：Resend 免费版每天限额 100 封，每月 3000 封。
2.  **API Key 安全**：如果 API Key 泄露，请在 Resend 后台删除并重新生成，同步更新 `.env`。
3.  **域名验证**：确保 Cloudflare 中的 DKIM 记录保持激活状态（灰云）。

## 3. 测试连通性

可以运行 `scripts/test_resend_smtp.py` 脚本验证配置是否正确。

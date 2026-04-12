#!/bin/sh
set -e

# 初始化数据库（两个服务都可能首先运行，幂等）
python -c "from models import init_db; init_db()"

case "${SERVICE}" in
  smtp)
    echo "[entrypoint] 启动 SMTP 转发服务..."
    exec python smtp_server.py
    ;;
  api)
    echo "[entrypoint] 启动 API 服务..."
    exec gunicorn api:app \
      --bind 0.0.0.0:5000 \
      --workers 2 \
      --timeout 60 \
      --access-logfile - \
      --error-logfile -
    ;;
  *)
    echo "请设置环境变量 SERVICE=smtp 或 SERVICE=api"
    exit 1
    ;;
esac

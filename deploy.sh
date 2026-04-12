#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║         邮件转发商城 —— 一键部署脚本                                ║
# ║         适用：CentOS 10 / Google Cloud VPS                          ║
# ╚══════════════════════════════════════════════════════════════════════╝
set -euo pipefail

# ── 颜色输出 ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
title()   { echo -e "\n${BOLD}${CYAN}══ $* ══${NC}\n"; }

# ── 必须以 root 运行 ────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "请使用 root 运行: sudo bash deploy.sh"

# ── 收集配置 ────────────────────────────────────────────────────────────
title "邮件转发系统 一键部署"

echo -e "${BOLD}请填写以下配置（直接回车使用括号内默认值）${NC}\n"

read -rp "你的域名 [flapysun.com]: " MY_DOMAIN
MY_DOMAIN="${MY_DOMAIN:-flapysun.com}"

echo ""
echo "外发 SMTP 配置（用于把邮件转发给用户）"
echo "推荐：Gmail 应用专用密码  或  SendGrid / Mailgun"
read -rp "SMTP 服务器 [smtp.gmail.com]: " SMTP_OUT_HOST
SMTP_OUT_HOST="${SMTP_OUT_HOST:-smtp.gmail.com}"

read -rp "SMTP 端口 [587]: " SMTP_OUT_PORT
SMTP_OUT_PORT="${SMTP_OUT_PORT:-587}"

read -rp "SMTP 用户名（你的发件邮箱）: " SMTP_OUT_USER
[[ -z "$SMTP_OUT_USER" ]] && error "SMTP 用户名不能为空"

read -rsp "SMTP 密码（输入不显示）: " SMTP_OUT_PASS; echo
[[ -z "$SMTP_OUT_PASS" ]] && error "SMTP 密码不能为空"

read -rp "发件人地址 [forward@${MY_DOMAIN}]: " SMTP_OUT_FROM
SMTP_OUT_FROM="${SMTP_OUT_FROM:-forward@${MY_DOMAIN}}"

# 生成随机 API Key
DEFAULT_API_KEY=$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32 || true)
read -rp "API Key（商城后台鉴权用）[${DEFAULT_API_KEY}]: " API_KEY
API_KEY="${API_KEY:-$DEFAULT_API_KEY}"

INSTALL_DIR="/opt/email-forwarder"

# ── 确认 ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}─────────── 配置确认 ───────────${NC}"
echo "  域名         : $MY_DOMAIN"
echo "  SMTP 服务器  : $SMTP_OUT_HOST:$SMTP_OUT_PORT"
echo "  SMTP 用户    : $SMTP_OUT_USER"
echo "  发件人       : $SMTP_OUT_FROM"
echo "  API Key      : $API_KEY"
echo "  安装目录     : $INSTALL_DIR"
echo -e "${BOLD}────────────────────────────────${NC}\n"
read -rp "确认开始安装？[y/N]: " CONFIRM
[[ "${CONFIRM,,}" != "y" ]] && { warn "已取消"; exit 0; }

# ════════════════════════════════════════════════════════════════════════
title "1/6  系统更新 & 基础依赖"
# ════════════════════════════════════════════════════════════════════════
dnf update -y -q
dnf install -y -q curl wget git firewalld
success "系统依赖安装完成"

# ════════════════════════════════════════════════════════════════════════
title "2/6  安装 Docker & Docker Compose"
# ════════════════════════════════════════════════════════════════════════
if ! command -v docker &>/dev/null; then
    info "安装 Docker..."
    dnf install -y -q dnf-plugins-core
    dnf config-manager --add-repo \
        https://download.docker.com/linux/centos/docker-ce.repo
    dnf install -y -q docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    success "Docker 安装完成"
else
    success "Docker 已安装: $(docker --version)"
fi

# ════════════════════════════════════════════════════════════════════════
title "3/6  防火墙配置"
# ════════════════════════════════════════════════════════════════════════
systemctl enable --now firewalld

# 开放必要端口
for port in 25/tcp 80/tcp; do
    firewall-cmd --permanent --add-port="$port" 2>/dev/null || true
done
# Google Cloud 还需在控制台开放 25 和 80
firewall-cmd --reload
success "防火墙端口已开放: 25(SMTP), 80(HTTP)"

warn "⚠  Google Cloud 请确认在 VPC 防火墙规则中也放开了 TCP 25 和 TCP 80"

# ════════════════════════════════════════════════════════════════════════
title "4/6  部署项目文件"
# ════════════════════════════════════════════════════════════════════════
mkdir -p "$INSTALL_DIR"

# 写入 .env
cat > "$INSTALL_DIR/.env" <<EOF
MY_DOMAIN=${MY_DOMAIN}
SMTP_OUT_HOST=${SMTP_OUT_HOST}
SMTP_OUT_PORT=${SMTP_OUT_PORT}
SMTP_OUT_USER=${SMTP_OUT_USER}
SMTP_OUT_PASS=${SMTP_OUT_PASS}
SMTP_OUT_FROM=${SMTP_OUT_FROM}
API_KEY=${API_KEY}
EOF
chmod 600 "$INSTALL_DIR/.env"

# 复制项目文件
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -r "$SCRIPT_DIR/app"    "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/nginx"  "$INSTALL_DIR/"
cp    "$SCRIPT_DIR/docker-compose.yml" "$INSTALL_DIR/"

success "项目文件已复制到 $INSTALL_DIR"

# ════════════════════════════════════════════════════════════════════════
title "5/6  构建 & 启动 Docker 容器"
# ════════════════════════════════════════════════════════════════════════
cd "$INSTALL_DIR"
docker compose down --remove-orphans 2>/dev/null || true
docker compose build --no-cache
docker compose up -d
success "容器启动完成"

# ════════════════════════════════════════════════════════════════════════
title "6/6  验证服务状态"
# ════════════════════════════════════════════════════════════════════════
sleep 5
docker compose ps

# 健康检查
if curl -sf http://localhost/health > /dev/null; then
    success "API 服务正常运行"
else
    warn "API 服务可能还在启动中，稍后可运行: curl http://localhost/health"
fi

# ── 安装完成提示 ────────────────────────────────────────────────────────
VPS_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_VPS_IP")

echo ""
echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║              部署完成！                                 ║${NC}"
echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}下一步：在 Cloudflare 配置 DNS${NC}"
echo ""
echo -e "  1. MX 记录："
echo -e "     名称: ${CYAN}${MY_DOMAIN}${NC}"
echo -e "     内容: ${CYAN}mail.${MY_DOMAIN}${NC}  优先级: 10"
echo ""
echo -e "  2. A  记录："
echo -e "     名称: ${CYAN}mail.${MY_DOMAIN}${NC}"
echo -e "     内容: ${CYAN}${VPS_IP}${NC}  （关闭小云朵代理）"
echo ""
echo -e "${BOLD}管理接口${NC}"
echo -e "  健康检查  : http://${VPS_IP}/health"
echo -e "  用户设置  : http://${VPS_IP}/setup?e=邮箱前缀&o=订单ID"
echo ""
echo -e "${BOLD}API 示例（需要 X-API-Key: ${API_KEY} 请妥善保存）${NC}"
echo ""
echo -e "  # 分配邮箱"
echo -e "  ${CYAN}curl -X POST http://${VPS_IP}/api/email/assign \\${NC}"
echo -e "  ${CYAN}     -H 'X-API-Key: ${API_KEY}' \\${NC}"
echo -e "  ${CYAN}     -H 'Content-Type: application/json' \\${NC}"
echo -e "  ${CYAN}     -d '{\"local_part\":\"abc123\",\"order_id\":\"ORDER001\",\"buyer_name\":\"张三\"}'${NC}"
echo ""
echo -e "  # 查看转发日志"
echo -e "  ${CYAN}curl http://${VPS_IP}/api/email/logs -H 'X-API-Key: ${API_KEY}'${NC}"
echo ""
echo -e "${BOLD}常用运维命令${NC}"
echo -e "  查看日志   : cd ${INSTALL_DIR} && docker compose logs -f"
echo -e "  重启服务   : cd ${INSTALL_DIR} && docker compose restart"
echo -e "  停止服务   : cd ${INSTALL_DIR} && docker compose down"
echo -e "  更新部署   : cd ${INSTALL_DIR} && docker compose pull && docker compose up -d --build"
echo ""

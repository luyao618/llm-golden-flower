#!/usr/bin/env bash
# ============================================================
# Golden Flower Poker AI - 一键部署脚本
#
# 用法:
#   首次部署（全新机器）:  ./deploy.sh --init
#   更新部署（拉取新代码）: ./deploy.sh
#   仅重启服务:            ./deploy.sh --restart
#   查看日志:              ./deploy.sh --logs
#   停止服务:              ./deploy.sh --stop
# ============================================================

set -euo pipefail

# ---- 配置 ----
REPO_URL="https://github.com/luyao618/llm-golden-flower.git"
PROJECT_DIR="$HOME/golden-flower"
HEALTH_URL="http://localhost/health"
HEALTH_TIMEOUT=60  # 健康检查最大等待秒数

# ---- 颜色输出 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ---- 健康检查 ----
health_check() {
    info "等待服务启动..."
    local elapsed=0
    while [ $elapsed -lt $HEALTH_TIMEOUT ]; do
        if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
            success "健康检查通过!"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        printf "."
    done
    echo ""
    error "健康检查超时 (${HEALTH_TIMEOUT}s)，请检查日志: docker compose logs"
    return 1
}

# ---- 显示服务状态 ----
show_status() {
    echo ""
    echo "==========================================="
    docker compose ps
    echo "==========================================="
    echo ""

    # 获取公网 IP
    local public_ip
    public_ip=$(curl -sf http://checkip.amazonaws.com 2>/dev/null || echo "未知")

    success "部署完成!"
    info "访问地址: http://${public_ip}"
    echo ""
    info "常用命令:"
    echo "  查看日志:   cd $PROJECT_DIR && docker compose logs -f backend"
    echo "  重启服务:   cd $PROJECT_DIR && ./deploy.sh --restart"
    echo "  停止服务:   cd $PROJECT_DIR && ./deploy.sh --stop"
    echo "  更新部署:   cd $PROJECT_DIR && ./deploy.sh"
}

# ---- 首次初始化 ----
cmd_init() {
    info "=== 首次部署初始化 ==="

    # 安装 Docker
    if ! command -v docker &> /dev/null; then
        info "安装 Docker..."
        curl -fsSL https://get.docker.com | sudo sh
        sudo usermod -aG docker "$USER"
        warn "Docker 用户组已添加，需要重新登录后再运行: ./deploy.sh --init"
        warn "请执行: exit 然后重新 SSH 登录，再运行 ./deploy.sh --init"
        exit 0
    else
        success "Docker 已安装: $(docker --version)"
    fi

    # 检查 docker compose
    if ! docker compose version &> /dev/null; then
        info "安装 Docker Compose 插件..."
        sudo apt-get update && sudo apt-get install -y docker-compose-plugin
    fi
    success "Docker Compose: $(docker compose version)"

    # 安装 git
    if ! command -v git &> /dev/null; then
        info "安装 Git..."
        sudo apt-get update && sudo apt-get install -y git
    fi

    # 克隆项目
    if [ ! -d "$PROJECT_DIR" ]; then
        info "克隆项目..."
        git clone "$REPO_URL" "$PROJECT_DIR"
    else
        warn "项目目录已存在，跳过克隆"
    fi

    cd "$PROJECT_DIR"

    # 创建 .env 文件
    if [ ! -f backend/.env ]; then
        info "创建环境变量文件..."
        cp backend/.env.example backend/.env
        warn "请编辑 backend/.env 配置 API Key（也可在前端页面动态配置）"
    fi

    # 构建并启动
    cmd_deploy

    echo ""
    warn "提醒: 请确保 Azure NSG 已开放 80 端口 (HTTP)"
}

# ---- 更新部署 ----
cmd_deploy() {
    cd "$PROJECT_DIR"

    info "=== 开始部署 ==="

    # 拉取最新代码
    if [ -d .git ]; then
        info "拉取最新代码..."
        git pull --ff-only || {
            warn "git pull 失败，可能有本地修改。尝试 git stash 后重试..."
            git stash
            git pull --ff-only
            git stash pop 2>/dev/null || true
        }
        success "代码已更新: $(git log -1 --format='%h %s')"
    fi

    # 构建并启动容器
    info "构建并启动容器（可能需要几分钟）..."
    docker compose up -d --build

    # 清理旧镜像
    info "清理未使用的 Docker 镜像..."
    docker image prune -f 2>/dev/null || true

    # 健康检查
    health_check

    # 显示状态
    show_status
}

# ---- 重启 ----
cmd_restart() {
    cd "$PROJECT_DIR"
    info "重启服务..."
    docker compose restart
    health_check
    show_status
}

# ---- 停止 ----
cmd_stop() {
    cd "$PROJECT_DIR"
    info "停止服务..."
    docker compose down
    success "服务已停止"
}

# ---- 查看日志 ----
cmd_logs() {
    cd "$PROJECT_DIR"
    docker compose logs -f --tail=100
}

# ---- 主入口 ----
case "${1:-}" in
    --init)
        cmd_init
        ;;
    --restart)
        cmd_restart
        ;;
    --stop)
        cmd_stop
        ;;
    --logs)
        cmd_logs
        ;;
    --help|-h)
        echo "用法: ./deploy.sh [选项]"
        echo ""
        echo "选项:"
        echo "  (无参数)    拉取最新代码并重新部署"
        echo "  --init      首次部署（安装 Docker、克隆代码、构建启动）"
        echo "  --restart   重启服务（不重新构建）"
        echo "  --stop      停止所有服务"
        echo "  --logs      查看实时日志"
        echo "  --help      显示此帮助信息"
        ;;
    *)
        cmd_deploy
        ;;
esac

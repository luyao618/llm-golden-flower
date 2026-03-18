#!/usr/bin/env bash
#
# 一键启动脚本 - 大模型炸金花 (LLM Golden Flower Poker)
#
# 功能:
#   1. 检查并安装依赖 (uv sync / npm install)
#   2. 构建前端 (如果需要)
#   3. 如有已运行的实例则重启
#   4. 启动后端和前端开发服务器
#   5. 自动打开浏览器到欢迎页面
#

set -euo pipefail

# ── 颜色定义 ──────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── 项目根目录 ────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOG_DIR="$PROJECT_DIR/.logs"
BACKEND_PID_FILE="$LOG_DIR/backend.pid"
FRONTEND_PID_FILE="$LOG_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

BACKEND_PORT=8000
FRONTEND_PORT=5173
WELCOME_URL="http://localhost:$FRONTEND_PORT"

# ── 辅助函数 ──────────────────────────────────────────────
info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*"; exit 1; }

banner() {
  echo -e "${BOLD}${CYAN}"
  echo "╔══════════════════════════════════════════╗"
  echo "║      🃏  大模型炸金花  LLM Golden Flower  ║"
  echo "║              一键启动脚本                ║"
  echo "╚══════════════════════════════════════════╝"
  echo -e "${NC}"
}

# 打开浏览器 (跨平台)
open_browser() {
  local url="$1"
  if command -v open &>/dev/null; then
    open "$url"                    # macOS
  elif command -v xdg-open &>/dev/null; then
    xdg-open "$url"               # Linux
  elif command -v wslview &>/dev/null; then
    wslview "$url"                 # WSL
  else
    warn "无法自动打开浏览器，请手动访问: $url"
  fi
}

# 等待服务就绪
wait_for_service() {
  local name="$1" url="$2" max_wait="${3:-30}"
  local elapsed=0
  info "等待 $name 启动..."
  while [ $elapsed -lt $max_wait ]; do
    if curl -s -o /dev/null -w '' "$url" 2>/dev/null; then
      success "$name 已就绪 ($url)"
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  warn "$name 在 ${max_wait}s 内未就绪，请检查日志: $LOG_DIR/"
  return 1
}

# ── 停止已有进程 ──────────────────────────────────────────
stop_existing() {
  local stopped=false

  # 通过 PID 文件停止
  for pid_file in "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"; do
    if [ -f "$pid_file" ]; then
      local pid
      pid=$(cat "$pid_file")
      if kill -0 "$pid" 2>/dev/null; then
        local name="backend"
        [[ "$pid_file" == *frontend* ]] && name="frontend"
        info "停止已有 $name 进程 (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
        # 等待进程退出
        for _ in $(seq 1 5); do
          kill -0 "$pid" 2>/dev/null || break
          sleep 1
        done
        # 强制终止
        kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null
        stopped=true
      fi
      rm -f "$pid_file"
    fi
  done

  # 通过端口查找并停止残留进程
  for port in $BACKEND_PORT $FRONTEND_PORT; do
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
      info "停止占用端口 $port 的进程..."
      echo "$pids" | xargs kill 2>/dev/null || true
      sleep 1
      # 强制终止残留
      pids=$(lsof -ti :"$port" 2>/dev/null || true)
      if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
      fi
      stopped=true
    fi
  done

  if $stopped; then
    success "已停止旧进程"
    sleep 1
  fi
}

# ── 前置检查 ──────────────────────────────────────────────
check_prerequisites() {
  info "检查环境依赖..."

  # Python
  if ! command -v python3 &>/dev/null; then
    error "未找到 python3，请先安装 Python 3.9+"
  fi

  # uv (Python 包管理器)
  if ! command -v uv &>/dev/null; then
    warn "未找到 uv，正在安装..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv &>/dev/null || error "uv 安装失败"
    success "uv 已安装"
  fi

  # Node.js
  if ! command -v node &>/dev/null; then
    error "未找到 node，请先安装 Node.js 18+"
  fi

  # npm
  if ! command -v npm &>/dev/null; then
    error "未找到 npm，请先安装 Node.js 18+ (包含 npm)"
  fi

  success "环境检查通过"
}

# ── 安装后端依赖 ──────────────────────────────────────────
setup_backend() {
  info "检查后端依赖..."

  if [ ! -d "$BACKEND_DIR" ]; then
    error "未找到 backend/ 目录"
  fi

  # 检查是否需要 uv sync
  local need_sync=false
  if [ ! -d "$BACKEND_DIR/.venv" ]; then
    need_sync=true
    info "未找到虚拟环境，将创建..."
  elif [ "$BACKEND_DIR/pyproject.toml" -nt "$BACKEND_DIR/uv.lock" ] 2>/dev/null; then
    need_sync=true
    info "pyproject.toml 有更新..."
  fi

  if $need_sync; then
    info "安装后端依赖 (uv sync)..."
    (cd "$BACKEND_DIR" && uv sync) || error "后端依赖安装失败"
    success "后端依赖已安装"
  else
    success "后端依赖已就绪"
  fi
}

# ── 安装并构建前端 ────────────────────────────────────────
setup_frontend() {
  info "检查前端依赖..."

  if [ ! -d "$FRONTEND_DIR" ]; then
    error "未找到 frontend/ 目录"
  fi

  # 检查是否需要 npm install
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    info "安装前端依赖 (npm install)..."
    (cd "$FRONTEND_DIR" && npm install) || error "前端依赖安装失败"
    success "前端依赖已安装"
  elif [ "$FRONTEND_DIR/package.json" -nt "$FRONTEND_DIR/node_modules/.package-lock.json" ] 2>/dev/null; then
    info "package.json 有更新，重新安装依赖..."
    (cd "$FRONTEND_DIR" && npm install) || error "前端依赖安装失败"
    success "前端依赖已更新"
  else
    success "前端依赖已就绪"
  fi
}

# ── 启动后端 ──────────────────────────────────────────────
start_backend() {
  info "启动后端服务 (port: $BACKEND_PORT)..."

  mkdir -p "$LOG_DIR"

  (cd "$BACKEND_DIR" && uv run uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    > "$BACKEND_LOG" 2>&1) &

  local pid=$!
  echo "$pid" > "$BACKEND_PID_FILE"
  info "后端进程 PID: $pid"
}

# ── 启动前端 ──────────────────────────────────────────────
start_frontend() {
  info "启动前端开发服务器 (port: $FRONTEND_PORT)..."

  mkdir -p "$LOG_DIR"

  (cd "$FRONTEND_DIR" && npm run dev -- --port "$FRONTEND_PORT" \
    > "$FRONTEND_LOG" 2>&1) &

  local pid=$!
  echo "$pid" > "$FRONTEND_PID_FILE"
  info "前端进程 PID: $pid"
}

# ── 清理函数 (Ctrl+C 退出时调用) ──────────────────────────
cleanup() {
  echo ""
  info "正在关闭服务..."
  for pid_file in "$BACKEND_PID_FILE" "$FRONTEND_PID_FILE"; do
    if [ -f "$pid_file" ]; then
      local pid
      pid=$(cat "$pid_file")
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
      fi
      rm -f "$pid_file"
    fi
  done
  # 确保端口释放
  for port in $BACKEND_PORT $FRONTEND_PORT; do
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    [ -n "$pids" ] && echo "$pids" | xargs kill 2>/dev/null || true
  done
  success "服务已关闭"
  exit 0
}

# ── 主流程 ────────────────────────────────────────────────
main() {
  banner
  trap cleanup SIGINT SIGTERM

  # 1. 前置检查
  check_prerequisites

  # 2. 停止已有进程
  stop_existing

  # 3. 安装依赖
  setup_backend
  setup_frontend

  # 4. 启动服务
  start_backend
  start_frontend

  # 5. 等待服务就绪
  echo ""
  wait_for_service "后端" "http://localhost:$BACKEND_PORT/health" 30
  wait_for_service "前端" "$WELCOME_URL" 30

  # 6. 打开浏览器
  echo ""
  success "所有服务已启动!"
  echo -e "${BOLD}"
  echo "  后端 API:  http://localhost:$BACKEND_PORT"
  echo "  前端页面:  $WELCOME_URL"
  echo -e "${NC}"
  info "正在打开浏览器..."
  open_browser "$WELCOME_URL"

  echo ""
  info "按 ${BOLD}Ctrl+C${NC} 停止所有服务"
  echo ""

  # 7. 保持前台运行，实时显示日志
  tail -f "$BACKEND_LOG" "$FRONTEND_LOG" 2>/dev/null || wait
}

main "$@"

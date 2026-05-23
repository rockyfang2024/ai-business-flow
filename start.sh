#!/bin/bash
# AI Business Flow - 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== AI Business Flow ===${NC}"

# 创建 data 目录
mkdir -p "$DATA_DIR"

# ─── 检查 Python 环境 ───
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python3 未安装，请先安装 Python 3.10+${NC}"
    exit 1
fi

# ─── 检查 Node.js 环境 ───
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js 未安装，请先安装 Node.js 18+${NC}"
    exit 1
fi

# ─── 检查 Prompt 模板是否存在 ───
PROMPT_PATH="$BACKEND_DIR/prompts/extraction-prompt.md"
if [ ! -f "$PROMPT_PATH" ]; then
    echo -e "${RED}✗ 缺少 Prompt 模板: $PROMPT_PATH${NC}"
    exit 1
fi

# ─── 安装后端依赖 ───
echo -e "${YELLOW}[1/3] 检查后端依赖...${NC}"
cd "$BACKEND_DIR"
if ! pip show fastapi &> /dev/null; then
    echo "  安装 Python 依赖..."
    pip install -r requirements.txt -q 2>/dev/null || true
fi

# ─── 安装前端依赖 ───
echo -e "${YELLOW}[2/3] 检查前端依赖...${NC}"
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    echo "  安装前端依赖..."
    npm install --silent 2>/dev/null || npm install
fi

# ─── 启动后端 ───
echo -e "${YELLOW}[3/3] 启动服务...${NC}"
cd "$BACKEND_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 等待后端就绪
sleep 3
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 后端已启动 (PID: $BACKEND_PID)"
else
    echo -e "${YELLOW}!${NC} 后端启动中，请稍候..."
    sleep 2
fi

# ─── 启动前端 ───
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}=== 服务已启动 ===${NC}"
echo -e "  前端: ${GREEN}http://localhost:3000${NC}"
echo -e "  后端: ${GREEN}http://localhost:8000${NC}"
echo -e "  API 文档: ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo -e "按 Ctrl+C 停止所有服务"
echo ""
echo "提示：首次使用请先点击右上角 ⚙️ 配置 LLM API Key"

# 等待退出
wait
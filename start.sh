#!/bin/bash
# Business Flow Skill Web - 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$SCRIPT_DIR/data"

# 创建 data 目录
mkdir -p "$DATA_DIR"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Business Flow Skill Web ===${NC}"

# 启动后端
echo -e "${YELLOW}[1/2] 启动后端 (FastAPI)...${NC}"
cd "$BACKEND_DIR"
pip install -r requirements.txt -q 2>/dev/null || true
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# 等待后端启动
sleep 3
curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "Backend OK" || echo "Backend may need a moment..."

# 启动前端
echo -e "${YELLOW}[2/2] 启动前端 (Next.js)...${NC}"
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo -e "${GREEN}=== 服务已启动 ===${NC}"
echo "后端: http://localhost:8000"
echo "前端: http://localhost:3000"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "Backend PID: $BACKEND_PID | Frontend PID: $FRONTEND_PID"

# 等待退出
wait
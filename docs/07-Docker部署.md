# 07 · Docker 部署

> 核心实现：`docker-compose.yml` + `backend/Dockerfile` + `frontend/Dockerfile`

## 一、架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                      Docker Host                              │
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────────────────────┐  │
│  │   abf-backend    │    │          abf-frontend            │  │
│  │  (FastAPI/8000)  │◄───│         (Next.js/3000)            │  │
│  │                  │    │  /api/* → http://backend:8000     │  │
│  └────────┬─────────┘    └──────────────────────────────────┘  │
│           │                                                        │
│  ┌────────▼─────────┐                                             │
│  │    abf-data     │  ← Named Volume（持久化数据）                │
│  │  (/app/data)    │                                             │
│  └─────────────────┘                                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  /business-flow-skill  ← Prompt 模板目录（:ro 只读）     │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 二、docker-compose.yml 详解

```yaml
services:
  backend:
    build:
      context: ./backend         # Dockerfile 在 backend/ 目录
      dockerfile: Dockerfile
    container_name: abf-backend
    ports:
      - "8000:8000"            # 宿主机:容器端口映射
    volumes:
      # ① 业务数据持久化（YAML 配置 + 用户上传的文档 + 生成的 knowledge）
      - abf-data:/app/data
      # ② llm_config.yaml 只读挂载（保护配置，防止容器内意外修改）
      - ./llm_config.yaml:/app/llm_config.yaml:ro
      # ③ Prompt 模板目录只读挂载
      - ${BUSINESS_FLOW_SKILL_PATH:-../business-flow-skill}:/business-flow-skill:ro
    environment:
      - PYTHONUNBUFFERED=1     # 日志实时输出到 docker logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: abf-frontend
    ports:
      - "3000:3000"
    environment:
      - API_URL=http://backend:8000   # 容器网络名，而非 localhost
      - NODE_ENV=production
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy  # 前端等后端健康后才启动

volumes:
  abf-data:                        # Named Volume，持久化 /app/data
```

## 三、关键设计决策

### 3.1 depends_on + healthcheck（服务就绪等待）

```yaml
depends_on:
  backend:
    condition: service_healthy
```

**为什么需要**：前端启动时后端还没就绪会导致首次请求失败。通过 `healthcheck` 检测后端就绪，且 `depends_on` 使用 `condition: service_healthy` 确保后端完全启动后再启动前端。

### 3.2 Named Volume 数据持久化

```yaml
volumes:
  - abf-data:/app/data
```

所有业务数据（YAML 配置、用户文档、生成的 knowledge 文件）存储在 `/app/data`，通过 Docker Named Volume `abf-data` 持久化。**容器删除重建数据不丢失**。

### 3.3 只读挂载保护

```yaml
- ./llm_config.yaml:/app/llm_config.yaml:ro       # :ro = read-only
- ${BUSINESS_FLOW_SKILL_PATH:-../business-flow-skill}:/business-flow-skill:ro
```

- `llm_config.yaml` 设为只读，防止容器内程序误改
- Prompt 模板目录设为只读，保证 AI 抽取的 Prompt 模板不被篡改

### 3.4 环境变量 PYTHONUNBUFFERED=1

```yaml
environment:
  - PYTHONUNBUFFERED=1
```

不加这个，Python 日志会缓冲，不实时输出到 `docker logs`。加了这个，`stdout` 无缓冲，日志实时可见。

### 3.5 API_URL 用容器网络名而非 localhost

```yaml
environment:
  - API_URL=http://backend:8000   # ✅ 容器内部网络
```

在 Docker Compose 同一网络中，容器之间通过 **service name**（即 `backend`）互相访问，而非 `localhost:8000`（那是容器自己的端口）。

## 四、后端 Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 依赖文件独立安装层（改 requirements.txt 时可复用缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 非 root 用户运行（安全）
USER 1000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**关键点**：
- `python:3.10-slim`：轻量基础镜像
- `--no-cache-dir`：减少镜像体积
- `USER 1000`：非 root 运行

## 五、前端 Dockerfile

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

RUN npm run build

CMD ["npm", "start"]
```

**关键点**：
- `node:18-alpine`：轻量 Node 基础镜像
- `npm ci`：根据 lockfile 精确安装（可重现）
- `npm run build`：Next.js 生产构建
- `npm start`：运行生产服务器（而非 `next dev`）

## 六、部署命令

### 一键启动
```bash
git clone git@github.com:rockyfang2024/ai-business-flow.git
cd ai-business-flow
git clone https://github.com/rockyfang2024/business-flow-skill.git ../business-flow-skill
docker compose up --build
# 访问 http://localhost:3000
```

### 停止服务
```bash
docker compose down
```

### 重构部署（代码变更后）
```bash
docker compose up --build
```

### 查看日志
```bash
docker compose logs -f         # 实时日志
docker compose logs backend   # 后端日志
docker compose logs frontend  # 前端日志
```

### 进入容器调试
```bash
docker exec -it abf-backend sh   # 后端容器
docker exec -it abf-frontend sh  # 前端容器
```

## 七、健康检查机制

### 后端健康检查
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```
- 访问 `GET /health`
- 成功返回 HTTP 200 → 健康
- 失败（curl 退出码非0）→ 不健康，3次重试后重启容器

### 前端健康检查
```yaml
healthcheck:
  test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"]
```
- Node.js 脚本发 HTTP GET 到本机 3000
- 返回 200 → 退出码 0（成功）
- 非 200 或连接失败 → 退出码 1（重试）

## 八、数据安全与恢复

### 备份（定时做）
```bash
# 备份 abf-data volume
docker run --rm \
  -v ai-business-flow_abf-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/abf-data-$(date +%Y%m%d).tar.gz -C /data .

# 备份 llm_config.yaml
cp llm_config.yaml llm_config.yaml.bak
```

### 恢复
```bash
# 停止服务
docker compose down

# 恢复 volume
docker run --rm \
  -v ai-business-flow_abf-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/abf-data-YYYYMMDD.tar.gz -C /data

# 重启服务
docker compose up -d
```

## 九、与本地开发的对比

| 对比项 | 本地开发 | Docker 部署 |
|--------|---------|------------|
| 后端启动 | `uvicorn app.main:app --reload` | `docker compose up` |
| 前端启动 | `next dev -p 3000` | `docker compose up` |
| 数据存储 | `~/.business-flow-data/` | Docker volume `abf-data` |
| 配置变更 | 直接改 `llm_config.yaml` | 重启容器 |
| 日志查看 | 终端实时 | `docker compose logs -f` |
| 多设备访问 | 仅 localhost | 任意设备 IP:3000 |
| 环境隔离 | 依赖宿主机环境 | 完全隔离 |
| 健康检查 | 无 | 自动检测 + 自动重启 |
| 服务依赖 | 手动控制顺序 | `depends_on + healthcheck` |
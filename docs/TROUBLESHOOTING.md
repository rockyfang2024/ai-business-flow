# 问题排查与解决方案

本文档记录 ai-business-flow 项目中遇到的各类技术问题及其解决方案，便于后续快速定位和解决。

---

## 目录

1. [跨域问题（CORS）](#1-跨域问题cors)
2. [重复响应问题](#2-重复响应问题)

---

## 1. 跨域问题（CORS）

### 问题描述

- 浏览器 Console 报错：`strict-origin-when-cross-origin`
- 请求 URL 显示为 `http://localhost:8000/api/...`（直接访问后端端口，绕过了前端代理）
- 前端 Settings 对话框中的"测试连接"按钮点击后无响应或报错

### 根因分析

前端代码中有两处地方**硬编码了后端地址** `http://localhost:8000`，绕过了 Next.js 的 `/api` 代理：

1. **SettingsDialog.tsx 第 452 行**（测试连接按钮）：
   ```tsx
   // ❌ 错误写法 - 硬编码直接请求后端 8000 端口，导致跨域
   const res = await fetch("http://localhost:8000/api/config/llm/test", { ... });

   // ✅ 正确写法 - 使用相对路径，经过 Next.js 代理，无跨域问题
   const res = await fetch("/api/config/llm/test", { ... });
   ```

2. **api.ts 中的 BASE_URL**：已经正确使用 `/api` 相对路径，**没有问题**

### 技术背景

Next.js 通过 `next.config.js` 的 `rewrites` 配置，将所有 `/api/*` 请求代理到后端：

```js
// next.config.js
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:8000/api/:path*',
    },
  ];
},
```

使用相对路径 `/api/...` 发送请求时，浏览器会将其视为**同域请求**，不会触发 CORS 检查。而硬编码 `http://localhost:8000/api/...` 会导致浏览器直接向后端 8000 端口发请求，此时：

- 浏览器发送 CORS preflight（OPTIONS）请求
- 后端 FastAPI 的 CORS middleware 检查 `Origin` 头是否在 `allow_origins` 列表中
- 如果不在，返回 400 或允许但实际请求仍受阻

### 解决方案

**修复 SettingsDialog.tsx**：将硬编码的后端地址改为相对路径 `/api`

```tsx
// 修复前
const res = await fetch("http://localhost:8000/api/config/llm/test", { ... });

// 修复后
const res = await fetch("/api/config/llm/test", { ... });
```

### 验证方法

```bash
# 1. Preflight 请求验证（应返回 200）
curl -X OPTIONS http://localhost:3000/api/config/llm/test \
  -H "Origin: http://43.160.205.9:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"

# 预期结果：HTTP 200 + access-control-allow-origin: http://43.160.205.9:3000

# 2. 实际请求验证
curl -X POST http://localhost:3000/api/config/llm/test \
  -H "Origin: http://43.160.205.9:3000" \
  -H "Content-Type: application/json" \
  -d '{"provider":"openrouter","model":"openai/gpt-4o","api_key":"test"}'

# 预期结果：HTTP 200 或 401（API Key 无效），但无 CORS 报错
```

### 预防措施

1. **始终使用相对路径** `/api` 作为前端 API 的 Base URL，不要硬编码 `localhost:8000`
2. 所有前端 API 调用统一通过 `api.ts` 中的 `BASE_URL = "/api"` 封装
3. 如果需要直接调用后端（仅限后端到后端的场景），确保在 FastAPI 的 CORS middleware `allow_origins` 中添加对应地址
4. 使用浏览器 DevTools Network 面板检查请求的 URL 和响应头，发现跨域问题及时排查

### 常见 CORS 排查清单

| 检查项 | 说明 |
|---|---|
| 请求 URL | 确认是 `/api/...` 相对路径，不是 `http://localhost:8000/api/...` |
| Preflight (OPTIONS) | 浏览器自动发 OPTIONS，检查返回是否 200 |
| `access-control-allow-origin` | 必须包含前端 Origin（当前前端 IP + 端口） |
| `access-control-allow-credentials` | 如果用 `credentials: include`，必须是 `true` |
| 后端 allow_origins | FastAPI CORS middleware 的 `allow_origins` 列表包含前端地址 |

---

## 2. 重复响应问题

### 问题描述

对话模式下，AI 的回答在前端显示**两次**。例如 AI 回复一条消息，页面上出现两条完全相同的回复。

### 根因分析

问题出在 `DialogueTab.tsx` 的 `handleSend` 函数中，存在两个问题：

1. **`setReply(res.reply)` 在条件分支之前无条件执行**，导致回复无论什么情况都会通过 `reply` state 渲染一次

2. **条件分支的两个分支逻辑完全相同**（`is_complete=true` 和 `is_complete=false` 都执行 `setHistory([...newHistory, ...])`），导致 history 里也添加了一次

```tsx
// ❌ 问题代码
const res = await api_query.dialogue(processId, userMsg, newHistory);
setReply(res.reply);  // 无条件执行 → 渲染一次

if (!res.is_complete) {
  setHistory([...newHistory, { role: "assistant", content: res.reply }]);
} else {
  setHistory([...newHistory, { role: "assistant", content: res.reply }]); // 完全重复！
}
```

### 解决方案

分离 `is_complete` 的两个分支，**互斥处理**：

```tsx
// ✅ 修复后
if (!res.is_complete) {
  // 非完成状态：添加到history，reply通过history渲染（避免重复）
  setHistory([...newHistory, { role: "assistant", content: res.reply }]);
  setReply(""); // 清空reply状态，防止同时从history和reply两个渠道渲染
} else {
  // 完成状态：history已是最新，reply用于最终一次渲染
  setReply(res.reply);
}
```

### 验证方法

1. 打开前端对话页面
2. 输入消息，发送
3. 观察 AI 回复是否只显示**一次**
4. 检查对话历史中消息数量是否正确递增

### 预防措施

1. 条件分支中注意区分不同分支的**实际处理逻辑**，不要写出完全相同的分支
2. 使用 `console.log` 或断点调试，验证 state 更新逻辑是否符合预期
3. 注意 React 的 state 更新是异步的，避免依赖上一个 state 值时出现竞态

---

## 3. 对话历史切换 Tab 后丢失

### 问题描述

在对话模式下进行多轮对话，切换到其他 Tab（如"文档"或"知识结构"）后，再切换回"对话" Tab，**对话历史全部消失**，需要重新开始。

### 根因分析

前端 `DialogueTab` 组件的 `history` 状态存储在 **React 组件内部**（`useState`）。当切换 Tab 时，`DialogueTab` 组件被卸载（unmount），再次切换回来时组件重新挂载，`history` 恢复为初始空数组 `[]`，之前的对话内容全部丢失。

后端虽然有 `_dialogue_history` 内存字典，但：
1. 每次请求时后端**没有持久化**对话历史到磁盘
2. 前端每次发消息都携带完整的 `history`，但后端**没有真正使用**这个 history（之前直接覆盖）

### 解决方案

**后端改造**：将对话历史持久化到 `processes/{processId}/dialogue_history.json` 文件中。

每次对话结束后（无论是否完成），都将对话写入文件：

```python
# 非完成状态：追加到历史文件
chat_history.append({"role": "user", "content": body.message})
chat_history.append({"role": "assistant", "content": raw_reply})
with open(history_file, "w", encoding="utf-8") as f:
    json.dump({"history": chat_history, "is_complete": False}, f, ensure_ascii=False)
```

前端在组件挂载时调用 `GET /api/query/dialogue/{processId}/history` 加载历史：

```tsx
useEffect(() => {
  if (mode !== "dialogue") return;
  api_dialogue.getHistory(processId)
    .then(({ history, is_complete }) => {
      if (history.length > 0) {
        setHistory(history);
      }
      if (is_complete) {
        setHistory([]); // 已完成则清空（对话已转为知识结构）
      }
    })
    .catch(() => { /* ignore */ });
}, [processId, mode]);
```

### 新增文件

- `GET /api/query/dialogue/{processId}/history` — 从 `dialogue_history.json` 加载历史

### 验证方法

1. 在对话 Tab 进行多轮对话（至少 2 轮）
2. 切换到"文档"或"知识结构" Tab
3. 再切换回"对话" Tab
4. 确认之前的对话历史**完整保留**

---

## 4. 对话完成后的知识结构未展示

### 问题描述

对话完成后（AI 回复包含 `is_complete: true`），对话内容已转换为知识结构（YAML 文件），但在"知识结构" Tab 中**看不到这些内容**，仍然显示"暂无数据"。

### 根因分析

对话完成后，后端将知识写入 `processes/main.yaml` 等文件，但 `get_knowledge` 接口只读取 `processes/` 目录下的文件。关键问题在于：

1. **knowledge.json 写入逻辑**：对话完成后，`extracted_data` 存入 `knowledge.json`，但这个文件**不在 `get_knowledge` 的读取范围内**
2. **`has_knowledge` 判断**：之前只检查 `processes/` 目录是否存在，没有检查 `knowledge.json`

### 解决方案

**后端**：
1. 对话完成时，将 `extracted_data` 写入 `knowledge.json` 并生成对应的 YAML 文件
2. `has_knowledge` 判断增加对 `knowledge.json` 的检查
3. `get_knowledge` 接口支持从 `knowledge.json` 读取并转换为 YAML 格式

**数据流**：

```
对话完成 → extracted_data 写入 knowledge.json + 生成 processes/main.yaml
         → has_knowledge = true（知识结构Tab可点击）
         → 知识结构Tab读取 processes/main.yaml 展示
```

### 验证方法

1. 在对话 Tab 完成对话流程（让 AI 说"我已收集到足够信息"触发 `is_complete`）
2. 切换到"知识结构" Tab
3. 确认能看到生成的 YAML 内容（如主流程、决策树等）

---

## 其他参考信息

### 后端端口说明

| 服务 | 端口 | 说明 |
|---|---|---|
| 前端 (Next.js) | 3000 | 用户直接访问的地址 |
| 后端 (FastAPI) | 8000 | 不直接暴露，前端通过 Next.js 代理访问 |
| 数据库 | 默认 SQLite | 保存在 backend 目录下 |

### Next.js rewrites 代理配置

位于 `frontend/next.config.js`，将 `/api/*` 转发到 `http://localhost:8000/api/*`。

---

*本文档持续更新*
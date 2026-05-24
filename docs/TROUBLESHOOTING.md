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

问题出在 `DialogueTab.tsx` 的 `handleSend` 函数中，对 `is_complete` 条件的处理有误：

```tsx
// ❌ 问题代码 - 两个分支完全相同，且 is_complete 判断无实际区分
if (!res.is_complete) {
  setHistory([...newHistory, { role: "assistant", content: res.reply }]);
} else {
  setHistory([...newHistory, { role: "assistant", content: res.reply }]);
}
```

无论 `is_complete` 是 `true` 还是 `false`，都执行了完全相同的 `setHistory` 操作，导致 AI 回复被添加两次。

此外，`setReply(res.reply)` 已经将回复存入 `reply` state，而 `{reply && ...}` 渲染逻辑也会显示这条消息，形成**重复渲染**。

### 解决方案

修正 `DialogueTab.tsx` 的条件分支逻辑：`reply` state 用于**实时渲染**，而 `history` 中保存**已确认的对话历史**：

```tsx
// ✅ 修复后
if (!res.is_complete) {
  setHistory([...newHistory, { role: "assistant", content: res.reply }]);
}
// is_complete 为 true 时，不重复添加到 history，只保留 reply 显示即可
```

这样：
- `reply` state 控制当前回复的实时显示（`{reply && ...}` 渲染块）
- `history` 只保存经过确认的历史消息（避免重复添加）

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
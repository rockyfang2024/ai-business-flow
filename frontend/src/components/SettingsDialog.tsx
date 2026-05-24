"use client";

import { useState, useEffect, useRef } from "react";
import styles from "./SettingsDialog.module.css";

// ─────────────────────────────────────────────────────────────────────────────
// Provider registry — mirrors backend llm_config.py PROVIDERS
// Grouped by ecosystem for display
// ─────────────────────────────────────────────────────────────────────────────

interface ProviderEntry {
  id: string;
  name: string;          // display name
  description: string;
  defaultBaseUrl: string;
  models: string[];      // curated model list per provider
  envHint: string;       // env var hint shown to user
}

const PROVIDER_GROUPS: { group: string; providers: ProviderEntry[] }[] = [
  {
    group: "🌐 OpenRouter 生态",
    providers: [
      {
        id: "openrouter",
        name: "OpenRouter",
        description: "200+ 模型统一入口，支持路由策略与响应缓存",
        defaultBaseUrl: "https://openrouter.ai/api/v1",
        models: [
          "anthropic/claude-sonnet-4.6",
          "anthropic/claude-3-5-sonnet-20241022",
          "openai/gpt-5.4",
          "deepseek/deepseek-chat",
          "google/gemini-3-flash-preview",
          "qwen/qwen3-plus",
          "mistralai/mistral-nemo",
          "meta-llama/llama-3.3-70b-instruct",
        ],
        envHint: "OPENROUTER_API_KEY",
      },
    ],
  },
  {
    group: "🤖 Anthropic",
    providers: [
      {
        id: "anthropic",
        name: "Anthropic",
        description: "Claude 系列（API Key 认证）",
        defaultBaseUrl: "https://api.anthropic.com",
        models: [
          "claude-opus-4-6-20251101",
          "claude-sonnet-4.6",
          "claude-haiku-4-5-20251001",
          "claude-3-5-sonnet-20241022",
          "claude-3-5-haiku-20241022",
          "claude-3-opus-20240229",
          "claude-3-haiku-20240307",
        ],
        envHint: "ANTHROPIC_API_KEY",
      },
      {
        id: "bedrock",
        name: "AWS Bedrock",
        description: "Claude / Nova / Llama（AWS IAM 认证）",
        defaultBaseUrl: "",
        models: [
          "anthropic.claude-opus-4-6-20251101",
          "anthropic.claude-sonnet-4-6-20251101",
          "anthropic.claude-haiku-4-7-20260320",
          "us.meta.llama4-scout-17b-16e-instruct-v1",
          "amazon.nova-pro-1-0",
        ],
        envHint: "AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS_REGION",
      },
    ],
  },
  {
    group: "🔍 Google",
    providers: [
      {
        id: "gemini",
        name: "Google AI Studio",
        description: "Gemini 系列（Gemini API）",
        defaultBaseUrl: "https://generativelanguage.googleapis.com/v1beta",
        models: [
          "gemini-2.5-flash-preview",
          "gemini-2.0-flash",
          "gemini-1.5-flash",
          "gemini-1.5-pro",
          "gemini-1.0-pro",
        ],
        envHint: "GEMINI_API_KEY",
      },
    ],
  },
  {
    group: "🧠 中国大模型",
    providers: [
      {
        id: "deepseek",
        name: "DeepSeek",
        description: "DeepSeek-V3 / R1 / Coder",
        defaultBaseUrl: "https://api.deepseek.com/v1",
        models: [
          "deepseek-chat",
          "deepseek-reasoner",
          "deepseek-coder",
        ],
        envHint: "DEEPSEEK_API_KEY",
      },
      {
        id: "kimi-coding",
        name: "Kimi / Moonshot（国际）",
        description: "Kimi 国际版 API（Moonshot AI）",
        defaultBaseUrl: "https://api.moonshot.ai/v1",
        models: [
          "kimi-k2.6",
          "kimi-k2.5",
          "kimi-for-coding",
          "kimi-k2-thinking",
          "kimi-k2-thinking-turbo",
          "moonshot-v1-8k",
          "moonshot-v1-32k",
          "moonshot-v1-128k",
        ],
        envHint: "KIMI_API_KEY",
      },
      {
        id: "kimi-coding-cn",
        name: "Kimi / Moonshot（国内）",
        description: "Kimi 国内版 API（moonshot.cn）",
        defaultBaseUrl: "https://api.moonshot.cn/v1",
        models: [
          "kimi-k2.6",
          "kimi-k2.5",
          "moonshot-v1-8k",
          "moonshot-v1-32k",
          "moonshot-v1-128k",
        ],
        envHint: "KIMI_API_KEY",
      },
      {
        id: "alibaba",
        name: "阿里云通义 (DashScope)",
        description: "Qwen / 多模型聚合（国际版）",
        defaultBaseUrl: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        models: [
          "qwen-plus",
          "qwen-plus-2",
          "qwen-turbo",
          "qwen-max",
          "qwen-long",
          "qwen-coder-plus",
        ],
        envHint: "DASHSCOPE_API_KEY",
      },
      {
        id: "minimax",
        name: "MiniMax（国际）",
        description: "MiniMax 国际版 API（支持 MiniMax-M2.7）",
        defaultBaseUrl: "https://api.minimax.io/anthropic",
        models: [
          "MiniMax-M2.7",
          "MiniMax-M2.5",
          "MiniMax-M2.1",
          "MiniMax-M2",
        ],
        envHint: "MINIMAX_API_KEY",
      },
      {
        id: "minimax-cn",
        name: "MiniMax（中国）",
        description: "MiniMax 国内版 API（支持 MiniMax-M2.7）",
        defaultBaseUrl: "https://api.minimaxi.com/anthropic",
        models: [
          "MiniMax-M2.7",
          "MiniMax-M2.5",
          "MiniMax-M2.1",
          "MiniMax-M2",
        ],
        envHint: "MINIMAX_CN_API_KEY",
      },
      {
        id: "xiaomi",
        name: "小米 MiMo",
        description: "MiMo-V2 系列（pro / omni / flash）",
        defaultBaseUrl: "https://api.xiaomimimo.com/v1",
        models: [
          "mimo-v2-pro",
          "mimo-v2-omni",
          "mimo-v2-flash",
        ],
        envHint: "XIAOMI_API_KEY",
      },
      {
        id: "stepfun",
        name: "阶跃星辰 Stepfun",
        description: "Step 系列模型",
        defaultBaseUrl: "",
        models: [
          "step-1v-32k",
          "step-1-8k",
        ],
        envHint: "STEPFUN_API_KEY",
      },
      {
        id: "gmi",
        name: "GMI Cloud",
        description: "多模型直连 API",
        defaultBaseUrl: "",
        models: ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"],
        envHint: "GMI_API_KEY",
      },
      {
        id: "novita",
        name: "Novita AI",
        description: "多模型聚合",
        defaultBaseUrl: "",
        models: ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-flash"],
        envHint: "NOVITA_API_KEY",
      },
    ],
  },
  {
    group: "🔓 开源 / 本地",
    providers: [
      {
        id: "huggingface",
        name: "Hugging Face",
        description: "20+ 开源模型推理端点",
        defaultBaseUrl: "https://huggingface.co/api/v1",
        models: [
          "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
          "Qwen/Qwen2.5-72B-Instruct",
          "mistralai/Mistral-Nemo-Instruct-2407",
          "deepseek-ai/DeepSeek-V3-0324",
        ],
        envHint: "HF_TOKEN",
      },
      {
        id: "ollama-cloud",
        name: "Ollama Cloud",
        description: "Ollama 云端托管模型（ollama.com）",
        defaultBaseUrl: "https://ollama.com/v1",
        models: ["llama3.3:70b", "qwen2.5:72b", "mistral:7b", "codellama:34b"],
        envHint: "OLLAMA_API_KEY",
      },
      {
        id: "custom",
        name: "自定义端点",
        description: "LM Studio / vLLM / Ollama / 任意 OpenAI 兼容 API",
        defaultBaseUrl: "http://localhost:11434/v1",
        models: ["auto（手动输入）"],
        envHint: "OPENAI_API_KEY（作为默认兜底）",
      },
    ],
  },
  {
    group: "💻 开发工具",
    providers: [
      {
        id: "openai-codex",
        name: "OpenAI Codex",
        description: "OpenAI Codex（codex_responses transport）",
        defaultBaseUrl: "https://chatgpt.com/backend-api/codex",
        models: ["codex"],
        envHint: "OPENAI_API_KEY",
      },
      {
        id: "copilot",
        name: "GitHub Copilot",
        description: "GitHub Copilot（GITHUB_TOKEN）",
        defaultBaseUrl: "",
        models: ["gpt-4o", "gpt-4-turbo"],
        envHint: "GITHUB_TOKEN",
      },
      {
        id: "nvidia",
        name: "NVIDIA NIM",
        description: "Nemotron / NIM 托管模型（build.nvidia.com）",
        defaultBaseUrl: "https://integrate.api.nvidia.com/v1",
        models: [
          "nvidia/llama-4-maverick-17b-16e-instruct",
          "nvidia/llama-4-scout-17b-16e-instruct",
          "nemotron-4-340b-instruct",
        ],
        envHint: "NVIDIA_API_KEY",
      },
      {
        id: "nous",
        name: "Nous Research",
        description: "Nous Portal（Nous Research 订阅）",
        defaultBaseUrl: "https://inference-api.nousresearch.com/v1",
        models: ["NousResearch/Meta-Llama-3.1-70B-Instruct"],
        envHint: "NOUS_API_KEY（OAuth device code）",
      },
      {
        id: "zai",
        name: "Z.AI / 智谱 GLM",
        description: "Zhipu AI 直连 API",
        defaultBaseUrl: "",
        models: ["glm-4-plus", "glm-4v", "glm-z1-32k"],
        envHint: "ZAI_API_KEY 或 GLM_API_KEY",
      },
      {
        id: "arcee",
        name: "Arcee AI",
        description: "Arcee Trinity 模型",
        defaultBaseUrl: "https://api.arcee.ai/api/v1",
        models: ["Arcee-Spark", "Arcee-Pro"],
        envHint: "ARCEEAI_API_KEY",
      },
      {
        id: "ai-gateway",
        name: "Vercel AI Gateway",
        description: "200+ 模型聚合网关",
        defaultBaseUrl: "",
        models: ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-flash"],
        envHint: "AI_GATEWAY_API_KEY 或 VERCEL_API_KEY",
      },
      {
        id: "kilocode",
        name: "Kilo Code",
        description: "Kilo Gateway API",
        defaultBaseUrl: "",
        models: ["gpt-4o", "claude-3-5-sonnet"],
        envHint: "KILOCODE_API_KEY",
      },
      {
        id: "opencode-zen",
        name: "OpenCode Zen",
        description: "35+ 精选模型（按量付费）",
        defaultBaseUrl: "",
        models: ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-flash"],
        envHint: "OPENCODE_ZEN_API_KEY",
      },
      {
        id: "opencode-go",
        name: "OpenCode Go",
        description: "开源模型（$10/月订阅）",
        defaultBaseUrl: "",
        models: ["llama-3.3-70b", "qwen2.5-72b"],
        envHint: "OPENCODE_GO_API_KEY",
      },
      {
        id: "qwen-oauth",
        name: "Qwen OAuth",
        description: "Qwen Portal（复用本地 Qwen CLI 登录）",
        defaultBaseUrl: "https://portal.qwen.ai/v1",
        models: ["qwen-plus", "qwen-turbo", "qwen-max"],
        envHint: "QWEN_API_KEY",
      },
      {
        id: "alibaba-coding-plan",
        name: "阿里云 Coding Plan",
        description: "Qwen + 多提供商编程模型",
        defaultBaseUrl: "https://dashscope.aliyuncs.com/v1",
        models: ["qwen-coder-plus", "qwen-coder-7b"],
        envHint: "DASHSCOPE_API_KEY",
      },
    ],
  },
];

// Flatten for search
const ALL_PROVIDERS: ProviderEntry[] = PROVIDER_GROUPS.flatMap((g) => g.providers);

export interface LLMConfig {
  provider: string;
  model: string;
  apiKey: string;
  baseUrl: string;
}

const DEFAULT_CONFIG: LLMConfig = {
  provider: "openrouter",
  model: "anthropic/claude-sonnet-4.6",
  apiKey: "",
  baseUrl: "https://openrouter.ai/api/v1",
};

interface Props {
  open: boolean;
  onClose: () => void;
  config: LLMConfig;
  onSave: (config: LLMConfig) => void;
}

export default function SettingsDialog({ open, onClose, config, onSave }: Props) {
  const [form, setForm] = useState<LLMConfig>(DEFAULT_CONFIG);
  const [search, setSearch] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setForm(config);
    setSearch("");
    setShowDropdown(false);
    setTestResult(null);
  }, [config, open]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function getCurrentProvider(): ProviderEntry | undefined {
    return ALL_PROVIDERS.find((p) => p.id === form.provider);
  }

  function handleProviderSelect(p: ProviderEntry) {
    setForm({
      ...form,
      provider: p.id,
      model: p.models[0],
      baseUrl: p.defaultBaseUrl,
    });
    setSearch("");
    setShowDropdown(false);
    setTestResult(null);
  }

  function filteredGroups() {
    if (!search.trim()) return PROVIDER_GROUPS;
    const q = search.toLowerCase();
    return PROVIDER_GROUPS.map((g) => ({
      ...g,
      providers: g.providers.filter(
        (p) =>
          p.id.includes(q) ||
          p.name.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q)
      ),
    })).filter((g) => g.providers.length > 0);
  }

  async function handleTest() {
    if (!form.apiKey.trim()) {
      setTestResult({ ok: false, msg: "请先输入 API Key" });
      return;
    }
    setTestResult({ ok: true, msg: "正在连接测试..." });
    try {
      const res = await fetch("/api/config/llm/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: form.provider,
          model: form.model,
          api_key: form.apiKey,
          base_url: form.baseUrl,
        }),
      });
      const data = await res.json();
      if (res.ok && data.status === "ok") {
        setTestResult({ ok: true, msg: `✅ 连接成功：${data.response}` });
      } else {
        setTestResult({ ok: false, msg: `❌ ${data.detail || "连接失败"}` });
      }
    } catch (e: unknown) {
      setTestResult({ ok: false, msg: `❌ 网络错误：${e instanceof Error ? e.message : String(e)}` });
    }
  }

  function handleSave() {
    if (!form.apiKey.trim()) {
      alert("请输入 API Key");
      return;
    }
    onSave(form);
    onClose();
  }

  const provider = getCurrentProvider();

  if (!open) return null;

  return (
    <div className={styles.overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={styles.dialog}>
        {/* Header */}
        <div className={styles.header}>
          <h2 className={styles.title}>⚙️ LLM 设置</h2>
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div className={styles.body}>
          {/* Provider selector */}
          <div className={styles.field} ref={dropdownRef}>
            <label className={styles.label}>提供商</label>
            <div className={styles.searchWrapper}>
              <input
                type="text"
                className={styles.searchInput}
                placeholder="搜索或选择 Provider..."
                value={showDropdown ? search : `${provider?.name || form.provider}`}
                onFocus={() => setShowDropdown(true)}
                onChange={(e) => { setSearch(e.target.value); setShowDropdown(true); }}
              />
              <button
                className={styles.dropdownToggle}
                onClick={() => setShowDropdown((v) => !v)}
                type="button"
              >
                {showDropdown ? "▲" : "▼"}
              </button>
            </div>

            {showDropdown && (
              <div className={styles.dropdown}>
                {filteredGroups().map((group) => (
                  <div key={group.group}>
                    <div className={styles.groupLabel}>{group.group}</div>
                    {group.providers.map((p) => (
                      <div
                        key={p.id}
                        className={`${styles.providerItem} ${p.id === form.provider ? styles.active : ""}`}
                        onClick={() => handleProviderSelect(p)}
                      >
                        <span className={styles.providerName}>{p.name}</span>
                        <span className={styles.providerDesc}>{p.description}</span>
                      </div>
                    ))}
                  </div>
                ))}
                {filteredGroups().length === 0 && (
                  <div className={styles.noResults}>无匹配 Provider</div>
                )}
              </div>
            )}
          </div>

          {/* Base URL */}
          <div className={styles.field}>
            <label className={styles.label}>Base URL</label>
            <input
              type="text"
              className={styles.input}
              value={form.baseUrl}
              onChange={(e) => setForm({ ...form, baseUrl: e.target.value })}
              placeholder={provider?.defaultBaseUrl || "https://..."}
            />
            {provider && provider.defaultBaseUrl && (
              <span className={styles.hint}>默认: {provider.defaultBaseUrl}</span>
            )}
          </div>

          {/* API Key */}
          <div className={styles.field}>
            <label className={styles.label}>
              API Key
              {provider && (
                <span className={styles.envHint}>（环境变量: {provider.envHint}）</span>
              )}
            </label>
            <input
              type="password"
              className={styles.input}
              value={form.apiKey}
              onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
              placeholder="sk-... / 输入 API Key"
            />
          </div>

          {/* Model */}
          <div className={styles.field}>
            <label className={styles.label}>模型</label>
            <select
              className={styles.select}
              value={form.model}
              onChange={(e) => setForm({ ...form, model: e.target.value })}
            >
              {provider?.models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          {/* Test result */}
          {testResult && (
            <div className={`${styles.testResult} ${testResult.ok && testResult.msg.includes("成功") ? styles.testOk : styles.testFail}`}>
              {testResult.msg}
            </div>
          )}
        </div>

        <div className={styles.footer}>
          <button
            type="button"
            className={styles.testBtn}
            onClick={handleTest}
          >
            🔌 测试连接
          </button>
          <div className={styles.footerRight}>
            <button className={styles.cancelBtn} onClick={onClose}>取消</button>
            <button className={styles.saveBtn} onClick={handleSave}>保存</button>
          </div>
        </div>
      </div>
    </div>
  );
}
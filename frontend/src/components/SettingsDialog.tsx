"use client";

import { useState, useEffect } from "react";
import styles from "./SettingsDialog.module.css";

export interface LLMConfig {
  provider: string;
  model: string;
  apiKey: string;
  baseUrl: string;
}

const DEFAULT_CONFIG: LLMConfig = {
  provider: "openai",
  model: "gpt-4o",
  apiKey: "",
  baseUrl: "https://api.openai.com/v1",
};

const PROVIDER_MODELS: Record<string, { models: string[]; defaultBaseUrl: string; hint: string }> = {
  openai: {
    models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    defaultBaseUrl: "https://api.openai.com/v1",
    hint: "默认: https://api.openai.com/v1",
  },
  minimax: {
    models: ["MiniMax-Text-01", "MiniMax-Text-01-mini", "abab6.5s-chat", "abab6.5g-chat"],
    defaultBaseUrl: "https://api.minimax.chat/v1",
    hint: "MiniMax API: https://api.minimax.chat/v1",
  },
  "openai-compatible": {
    models: [
      "gpt-4o", "gpt-4o-mini",
      "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307",
      "deepseek-chat", "moonshot-v1-8k", "qwen-plus",
    ],
    defaultBaseUrl: "https://api.openai.com/v1",
    hint: "例如: http://localhost:11434/v1 (Ollama) 或其他 OpenAI 兼容 API",
  },
};

interface Props {
  open: boolean;
  onClose: () => void;
  config: LLMConfig;
  onSave: (config: LLMConfig) => void;
}

const PROVIDER_BUTTONS: { id: string; label: string }[] = [
  { id: "openai", label: "☁️ OpenAI 官方" },
  { id: "minimax", label: "🔵 MiniMax" },
  { id: "openai-compatible", label: "🔗 OpenAI 兼容" },
];

export default function SettingsDialog({ open, onClose, config, onSave }: Props) {
  const [form, setForm] = useState<LLMConfig>(DEFAULT_CONFIG);

  useEffect(() => {
    setForm(config);
  }, [config, open]);

  if (!open) return null;

  const providerInfo = PROVIDER_MODELS[form.provider] || PROVIDER_MODELS["openai"];
  const models = providerInfo.models;

  function handleProviderChange(p: string) {
    const info = PROVIDER_MODELS[p];
    setForm({ ...form, provider: p, model: info.models[0], baseUrl: info.defaultBaseUrl });
  }

  function handleSave() {
    if (!form.apiKey.trim()) {
      alert("请输入 API Key");
      return;
    }
    onSave(form);
    onClose();
  }

  return (
    <div className={styles.overlay} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className={styles.dialog}>
        <div className={styles.header}>
          <h2 className={styles.title}>⚙️ LLM 设置</h2>
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div className={styles.body}>
          {/* Provider */}
          <div className={styles.field}>
            <label className={styles.label}>提供商</label>
            <div className={styles.providerGroup}>
              {PROVIDER_BUTTONS.map((btn) => (
                <button
                  key={btn.id}
                  className={`${styles.providerBtn} ${form.provider === btn.id ? styles.activeProvider : ""}`}
                  onClick={() => handleProviderChange(btn.id)}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>

          {/* Base URL */}
          <div className={styles.field}>
            <label className={styles.label}>Base URL</label>
            <input
              type="text"
              className={styles.input}
              value={form.baseUrl}
              onChange={(e) => setForm({ ...form, baseUrl: e.target.value })}
              placeholder={providerInfo.defaultBaseUrl}
            />
            <span className={styles.hint}>{providerInfo.hint}</span>
          </div>

          {/* API Key */}
          <div className={styles.field}>
            <label className={styles.label}>API Key</label>
            <input
              type="password"
              className={styles.input}
              value={form.apiKey}
              onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
              placeholder="sk-... / MiniMax API Key"
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
              {models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>

        <div className={styles.footer}>
          <button className={styles.cancelBtn} onClick={onClose}>取消</button>
          <button className={styles.saveBtn} onClick={handleSave}>保存</button>
        </div>
      </div>
    </div>
  );
}
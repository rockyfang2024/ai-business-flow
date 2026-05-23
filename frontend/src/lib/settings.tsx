"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import type { LLMConfig } from "@/components/SettingsDialog";

const STORAGE_KEY = "bfs-llm-config";

const DEFAULT_CONFIG: LLMConfig = {
  provider: "openai",
  model: "gpt-4o",
  apiKey: "",
  baseUrl: "https://api.openai.com/v1",
};

interface SettingsContextValue {
  config: LLMConfig;
  updateConfig: (c: LLMConfig) => void;
  hasApiKey: boolean;
}

const SettingsContext = createContext<SettingsContextValue>({
  config: DEFAULT_CONFIG,
  updateConfig: () => {},
  hasApiKey: false,
});

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<LLMConfig>(DEFAULT_CONFIG);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as LLMConfig;
        // Ensure all fields exist
        setConfig({ ...DEFAULT_CONFIG, ...parsed });
      }
    } catch {
      // ignore
    }
  }, []);

  function updateConfig(c: LLMConfig) {
    setConfig(c);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(c));
  }

  const hasApiKey = Boolean(config.apiKey?.trim());

  return (
    <SettingsContext.Provider value={{ config, updateConfig, hasApiKey }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  return useContext(SettingsContext);
}
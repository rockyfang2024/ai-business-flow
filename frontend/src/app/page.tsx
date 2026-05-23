"use client";

import { useState, useEffect, createContext, useContext } from "react";
import ProcessList from "@/components/ProcessList";
import ProcessDetail from "@/components/ProcessDetail";
import NewProcessDialog from "@/components/NewProcessDialog";
import SettingsDialog, { type LLMConfig } from "@/components/SettingsDialog";
import styles from "./page.module.css";
import type { ProcessListItem } from "@/types";

const STORAGE_KEY = "bfs-llm-config";

const DEFAULT_CONFIG: LLMConfig = {
  provider: "openai",
  model: "gpt-4o",
  apiKey: "",
  baseUrl: "https://api.openai.com/v1",
};

interface SettingsCtx {
  config: LLMConfig;
  updateConfig: (c: LLMConfig) => void;
}
const SettingsCtx = createContext<SettingsCtx>({ config: DEFAULT_CONFIG, updateConfig: () => {} });
export function useSettings() { return useContext(SettingsCtx); }

export default function HomePage() {
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [llmConfig, setLlmConfig] = useState<LLMConfig>(DEFAULT_CONFIG);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) setLlmConfig(JSON.parse(stored));
    } catch { /* ignore */ }
  }, []);

  function handleSettingsSave(cfg: LLMConfig) {
    setLlmConfig(cfg);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
  }

  function handleProcessCreated(id: string) {
    setSelectedProcessId(id);
    setDialogOpen(false);
    setRefreshKey((k) => k + 1);
  }

  return (
    <SettingsCtx.Provider value={{ config: llmConfig, updateConfig: handleSettingsSave }}>
      <div className={styles.shell}>
        {/* Left sidebar: process list */}
        <aside className={styles.sidebar}>
          <div className={styles.sidebarHeader}>
            <span className={styles.logo}>⚡ Business Flow</span>
            <div className={styles.headerActions}>
              <button className={styles.iconBtn} onClick={() => setSettingsOpen(true)} title="LLM 设置">
                ⚙️
              </button>
              <button className={styles.addBtn} onClick={() => setDialogOpen(true)} title="新建业务流程">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
              </button>
            </div>
          </div>
          <ProcessList
            selectedId={selectedProcessId}
            onSelect={setSelectedProcessId}
            refreshKey={refreshKey}
          />
        </aside>

        {/* Main content */}
        <main className={styles.main}>
          {selectedProcessId ? (
            <ProcessDetail processId={selectedProcessId} key={selectedProcessId} />
          ) : (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>📋</div>
              <h2>选择或创建一个业务流程</h2>
              <p>从左侧列表选择业务流程开始，或点击左上角 + 创建新的业务流程。</p>
            </div>
          )}
        </main>

        {/* New process dialog */}
        <NewProcessDialog open={dialogOpen} onClose={() => setDialogOpen(false)} onCreated={handleProcessCreated} />

        {/* Settings dialog */}
        <SettingsDialog
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          config={llmConfig}
          onSave={handleSettingsSave}
        />
      </div>
    </SettingsCtx.Provider>
  );
}
"use client";

import { useState } from "react";
import ProcessList from "@/components/ProcessList";
import ProcessDetail from "@/components/ProcessDetail";
import NewProcessDialog from "@/components/NewProcessDialog";
import styles from "./page.module.css";

export default function HomePage() {
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  function handleProcessCreated(id: string) {
    setSelectedProcessId(id);
    setDialogOpen(false);
    setRefreshKey((k) => k + 1);
  }

  return (
    <div className={styles.shell}>
      {/* 左侧边栏：业务流程列表 */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <span className={styles.logo}>⚡ Business Flow</span>
          <button className={styles.addBtn} onClick={() => setDialogOpen(true)} title="新建业务流程">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        </div>
        <ProcessList
          selectedId={selectedProcessId}
          onSelect={setSelectedProcessId}
          refreshKey={refreshKey}
        />
      </aside>

      {/* 主内容区 */}
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

      {/* 新建流程对话框 */}
      <NewProcessDialog open={dialogOpen} onClose={() => setDialogOpen(false)} onCreated={handleProcessCreated} />
    </div>
  );
}
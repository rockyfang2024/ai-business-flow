"use client";

import { useEffect, useState } from "react";
import { api_processes, api_extraction } from "@/lib/api";
import type { ProcessInfo, DocumentItem, ExtractionStatus, KnowledgeDoc } from "@/types";
import DocumentTab from "./tabs/DocumentTab";
import KnowledgeTab from "./tabs/KnowledgeTab";
import DialogueTab from "./tabs/DialogueTab";
import styles from "./ProcessDetail.module.css";

interface Props {
  processId: string;
}

type Tab = "docs" | "knowledge" | "dialogue";

export default function ProcessDetail({ processId }: Props) {
  const [process, setProcess] = useState<ProcessInfo | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("docs");
  const [extractionStatus, setExtractionStatus] = useState<ExtractionStatus | null>(null);

  useEffect(() => {
    api_processes.get(processId).then(setProcess).catch(console.error);
    api_extraction.getStatus(processId).then(setExtractionStatus).catch(console.error);
  }, [processId]);

  if (!process) {
    return <div className={styles.loading}>加载中...</div>;
  }

  const hasKnowledge = (process as ProcessInfo).has_knowledge;

  return (
    <div className={styles.container}>
      {/* 顶部 Header */}
      <div className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{process.name}</h1>
          {hasKnowledge && <span className={styles.badge}>已梳理</span>}
        </div>
        {process.description && (
          <p className={styles.description}>{process.description}</p>
        )}
      </div>

      {/* Tab 切换 */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === "docs" ? styles.activeTab : ""}`}
          onClick={() => setActiveTab("docs")}
        >
          📄 文档
        </button>
        <button
          className={`${styles.tab} ${activeTab === "knowledge" ? styles.activeTab : ""}`}
          onClick={() => setActiveTab("knowledge")}
          disabled={!hasKnowledge}
          title={!hasKnowledge ? "请先上传文档并完成抽取" : ""}
        >
          🧠 知识结构
        </button>
        <button
          className={`${styles.tab} ${activeTab === "dialogue" ? styles.activeTab : ""}`}
          onClick={() => setActiveTab("dialogue")}
        >
          💬 对话
        </button>
      </div>

      {/* Tab 内容 */}
      <div className={styles.content}>
        {activeTab === "docs" && (
          <DocumentTab
            processId={processId}
            onExtractionComplete={() => {
              api_extraction.getStatus(processId).then(setExtractionStatus);
              api_processes.get(processId).then(setProcess);
            }}
            extractionStatus={extractionStatus}
          />
        )}
        {activeTab === "knowledge" && hasKnowledge && (
          <KnowledgeTab processId={processId} />
        )}
        {activeTab === "dialogue" && (
          <DialogueTab
            processId={processId}
            hasKnowledge={hasKnowledge}
          />
        )}
      </div>
    </div>
  );
}
"use client";

import { useEffect, useState } from "react";
import { api_processes } from "@/lib/api";
import type { ProcessListItem } from "@/types";
import styles from "./ProcessList.module.css";

interface Props {
  selectedId: string | null;
  onSelect: (id: string) => void;
  refreshKey: number;
}

export default function ProcessList({ selectedId, onSelect, refreshKey }: Props) {
  const [processes, setProcesses] = useState<ProcessListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api_processes.list()
      .then(setProcesses)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [refreshKey]);

  if (loading) {
    return <div className={styles.loading}>加载中...</div>;
  }

  if (processes.length === 0) {
    return (
      <div className={styles.empty}>
        <p>暂无业务流程</p>
        <p className={styles.hint}>点击左上角 + 创建</p>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {processes.map((p) => (
        <button
          key={p.id}
          className={`${styles.item} ${selectedId === p.id ? styles.selected : ""}`}
          onClick={() => onSelect(p.id)}
        >
          <span className={styles.name}>{p.name}</span>
          {p.has_knowledge && <span className={styles.badge}>已梳理</span>}
          <span className={styles.date}>
            {new Date(p.updated_at).toLocaleDateString("zh-CN")}
          </span>
        </button>
      ))}
    </div>
  );
}
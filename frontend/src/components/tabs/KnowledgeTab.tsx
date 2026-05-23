"use client";

import { useEffect, useState } from "react";
import { api_processes } from "@/lib/api";
import type { KnowledgeDoc } from "@/types";
import styles from "./KnowledgeTab.module.css";

interface Props {
  processId: string;
}

export default function KnowledgeTab({ processId }: Props) {
  const [doc, setDoc] = useState<KnowledgeDoc | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeYaml, setActiveYaml] = useState<"main" | "decision-tree" | "exceptions" | "sla">("main");

  useEffect(() => {
    setLoading(true);
    api_processes.getKnowledge(processId)
      .then(setDoc)
      .catch(() => {
        setDoc({ main_yaml: "", decision_tree_yaml: "", exceptions_yaml: "", sla_yaml: "", skill_md: "" });
      })
      .finally(() => setLoading(false));
  }, [processId]);

  if (loading) {
    return <div className={styles.loading}>加载中...</div>;
  }

  const yamlContent =
    activeYaml === "main" ? doc?.main_yaml
    : activeYaml === "decision-tree" ? doc?.decision_tree_yaml
    : activeYaml === "exceptions" ? doc?.exceptions_yaml
    : doc?.sla_yaml;

  return (
    <div className={styles.container}>
      {/* YAML 选择器 */}
      <div className={styles.yamlSelector}>
        <button className={activeYaml === "main" ? styles.activeYaml : ""} onClick={() => setActiveYaml("main")}>主流程</button>
        <button className={activeYaml === "decision-tree" ? styles.activeYaml : ""} onClick={() => setActiveYaml("decision-tree")}>决策树</button>
        <button className={activeYaml === "exceptions" ? styles.activeYaml : ""} onClick={() => setActiveYaml("exceptions")}>异常矩阵</button>
        <button className={activeYaml === "sla" ? styles.activeYaml : ""} onClick={() => setActiveYaml("sla")}>SLA</button>
      </div>

      {/* YAML 内容 */}
      <div className={styles.yamlContent}>
        {yamlContent ? (
          <pre><code>{yamlContent}</code></pre>
        ) : (
          <div className={styles.empty}>暂无数据</div>
        )}
      </div>
    </div>
  );
}
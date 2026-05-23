"use client";

import { useEffect, useState, useRef } from "react";
import { api_processes, api_extraction } from "@/lib/api";
import type { DocumentItem, ExtractionStatus } from "@/types";
import styles from "./DocumentTab.module.css";

interface Props {
  processId: string;
  onExtractionComplete: () => void;
  extractionStatus: ExtractionStatus | null;
}

export default function DocumentTab({ processId, onExtractionComplete, extractionStatus }: Props) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [localPath, setLocalPath] = useState("");
  const [pathLoading, setPathLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  function loadDocs() {
    setLoading(true);
    api_processes.listDocuments(processId)
      .then(setDocuments)
      .catch(console.error)
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadDocs(); }, [processId]);

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith(".md")) {
      alert("目前只支持 .md 文件");
      return;
    }
    setUploading(true);
    try {
      const content = await file.text();
      await api_processes.uploadDocument(processId, file.name, content);
      await loadDocs();
    } catch (err) {
      alert(`上传失败: ${err}`);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function handlePathUpload() {
    if (!localPath.trim()) return;
    setPathLoading(true);
    try {
      await api_processes.uploadDocumentFromPath(processId, localPath.trim());
      setLocalPath("");
      await loadDocs();
    } catch (err) {
      alert(`上传失败: ${err}`);
    } finally {
      setPathLoading(false);
    }
  }

  async function handleExtract() {
    try {
      const result = await api_extraction.run(processId);
      if (result.status === "done" || result.status === "idle") {
        onExtractionComplete();
      }
    } catch (err) {
      alert(`抽取失败: ${err}`);
    }
  }

  const status = extractionStatus?.status ?? "idle";

  return (
    <div className={styles.container}>
      {/* 上传区 */}
      <div className={styles.uploadSection}>
        <div className={styles.uploadRow}>
          {/* 文件选择上传 */}
          <div className={styles.fileUpload}>
            <input
              ref={fileRef}
              type="file"
              accept=".md"
              onChange={handleFileUpload}
              style={{ display: "none" }}
            />
            <button
              className={styles.uploadBtn}
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "上传中..." : "📎 选择 Markdown 文件"}
            </button>
          </div>

          {/* 路径上传 */}
          <div className={styles.pathUpload}>
            <input
              type="text"
              placeholder="或输入本地文件路径：/home/user/docs/xx.md"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handlePathUpload()}
            />
            <button onClick={handlePathUpload} disabled={pathLoading || !localPath.trim()}>
              {pathLoading ? "..." : "上传"}
            </button>
          </div>
        </div>
      </div>

      {/* 文档列表 */}
      <div className={styles.docList}>
        <div className={styles.docListHeader}>
          <span>已上传文档（{documents.length}）</span>
        </div>
        {loading ? (
          <div className={styles.empty}>加载中...</div>
        ) : documents.length === 0 ? (
          <div className={styles.empty}>暂无文档，请上传 Markdown 文件或指定本地路径</div>
        ) : (
          <div className={styles.docs}>
            {documents.map((doc) => (
              <div key={doc.id} className={styles.docItem}>
                <span className={styles.docName}>{doc.filename}</span>
                <span className={styles.docMeta}>
                  {(doc.size / 1024).toFixed(1)} KB · {new Date(doc.uploaded_at).toLocaleString("zh-CN")}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 抽取操作 */}
      <div className={styles.extractSection}>
        <button
          className={styles.extractBtn}
          onClick={handleExtract}
          disabled={documents.length === 0 || status === "running"}
        >
          {status === "running" ? "⏳ AI 正在抽取..." : "🧠 开始 AI 知识抽取"}
        </button>
        {status === "error" && extractionStatus?.error && (
          <div className={styles.errorMsg}>错误：{extractionStatus.error}</div>
        )}
        {status === "done" && (
          <div className={styles.successMsg}>✅ 抽取完成，请切换到「知识结构」标签查看</div>
        )}
      </div>
    </div>
  );
}
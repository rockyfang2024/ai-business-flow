"use client";

import { useState } from "react";
import { api_processes } from "@/lib/api";
import styles from "./NewProcessDialog.module.css";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (id: string) => void;
}

export default function NewProcessDialog({ open, onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError("");
    try {
      const result = await api_processes.create({ name: name.trim(), description: description.trim() || undefined });
      onCreated(result.id);
      setName("");
      setDescription("");
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>新建业务流程</h2>
          <button className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label>业务流程名称 *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如：USDT 充币流程"
              autoFocus
              required
            />
          </div>
          <div className={styles.field}>
            <label>描述（可选）</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="简要描述这个业务流程..."
              rows={3}
            />
          </div>
          {error && <div className={styles.error}>{error}</div>}
          <div className={styles.actions}>
            <button type="button" className={styles.cancelBtn} onClick={onClose}>取消</button>
            <button type="submit" className={styles.submitBtn} disabled={loading || !name.trim()}>
              {loading ? "创建中..." : "创建"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
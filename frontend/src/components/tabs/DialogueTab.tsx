"use client";

import { useEffect, useState, useRef } from "react";
import { api_query } from "@/lib/api";
import type { DialogueTurn } from "@/types";
import styles from "./DialogueTab.module.css";

function getLLMConfig() {
  try {
    const stored = localStorage.getItem("bfs-llm-config");
    if (stored) return JSON.parse(stored);
  } catch { /* ignore */ }
  return { provider: "openai", model: "gpt-4o", apiKey: "", baseUrl: "https://api.openai.com/v1" };
}

function hasApiKey(): boolean {
  const cfg = getLLMConfig();
  return Boolean(cfg.apiKey?.trim());
}

interface Props {
  processId: string;
  hasKnowledge: boolean;
}

export default function DialogueTab({ processId, hasKnowledge }: Props) {
  const [mode, setMode] = useState<"query" | "dialogue">("query");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [apiKeyMissing, setApiKeyMissing] = useState(false);

  // Multi-turn dialogue state
  const [history, setHistory] = useState<DialogueTurn[]>([]);
  const [input, setInput] = useState("");
  const [dialogueLoading, setDialogueLoading] = useState(false);
  const [reply, setReply] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMode(hasKnowledge ? "query" : "dialogue");
  }, [hasKnowledge]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, reply]);

  async function handleQuery(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    if (!hasApiKey()) {
      setApiKeyMissing(true);
      return;
    }
    setApiKeyMissing(false);
    setLoading(true);
    setAnswer("");
    try {
      const res = await api_query.query(processId, question);
      setAnswer(res.answer);
    } catch (err) {
      setAnswer(`查询失败: ${err}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    if (!input.trim()) return;
    if (!hasApiKey()) {
      setApiKeyMissing(true);
      return;
    }
    setApiKeyMissing(false);
    const userMsg = input.trim();
    setInput("");
    setDialogueLoading(true);
    setReply("");

    const newHistory: DialogueTurn[] = [...history, { role: "user", content: userMsg }];
    setHistory(newHistory);

    try {
      const res = await api_query.dialogue(processId, userMsg, newHistory);
      setReply(res.reply);

      if (!res.is_complete) {
        setHistory([...newHistory, { role: "assistant", content: res.reply }]);
      } else {
        setHistory([...newHistory, { role: "assistant", content: res.reply }]);
      }
    } catch (err) {
      const errMsg = `错误: ${err}`;
      setReply(errMsg);
      setHistory([...newHistory, { role: "assistant", content: errMsg }]);
    } finally {
      setDialogueLoading(false);
    }
  }

  return (
    <div className={styles.container}>
      {/* API Key missing warning */}
      {apiKeyMissing && (
        <div className={styles.warning}>
          ⚠️ 请先在右上角 ⚙️ 设置中配置 LLM API Key
        </div>
      )}

      {/* Mode toggle */}
      <div className={styles.modeToggle}>
        <button
          className={mode === "query" ? styles.activeMode : ""}
          onClick={() => setMode("query")}
          disabled={!hasKnowledge}
        >
          🔍 知识问答
        </button>
        <button
          className={mode === "dialogue" ? styles.activeMode : ""}
          onClick={() => setMode("dialogue")}
        >
          💬 对话梳理
        </button>
      </div>

      {mode === "query" ? (
        /* ── Knowledge Query Mode ── */
        <div className={styles.queryMode}>
          <form onSubmit={handleQuery} className={styles.queryForm}>
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="输入你的业务问题，例如：韩国用户充值排名前10怎么查？"
              className={styles.queryInput}
            />
            <button type="submit" className={styles.sendBtn} disabled={loading || !question.trim()}>
              {loading ? "..." : "提问"}
            </button>
          </form>
          <div className={styles.answerArea}>
            {loading ? (
              <div className={styles.loadingDots}>AI 思考中<span>.</span><span>.</span><span>.</span></div>
            ) : answer ? (
              <div className={styles.answer}>{answer}</div>
            ) : (
              <div className={styles.answerPlaceholder}>
                AI 将基于已抽取的知识结构回答你的问题
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ── Dialogue Mode ── */
        <div className={styles.dialogueMode}>
          <div className={styles.intro}>
            💡 通过多轮对话梳理业务流程。AI 会向你提问，请耐心回答。回答完毕后会自动生成结构化文档。
          </div>
          <div className={styles.messages}>
            {history.map((turn, i) => (
              <div key={i} className={`${styles.turn} ${turn.role === "user" ? styles.userTurn : styles.assistantTurn}`}>
                <div className={styles.turnLabel}>{turn.role === "user" ? "你" : "AI"}</div>
                <div className={styles.turnContent}>{turn.content}</div>
              </div>
            ))}
            {reply && (
              <div className={`${styles.turn} ${styles.assistantTurn}`}>
                <div className={styles.turnLabel}>AI</div>
                <div className={styles.turnContent}>{reply}</div>
              </div>
            )}
            {dialogueLoading && (
              <div className={`${styles.turn} ${styles.assistantTurn}`}>
                <div className={styles.turnLabel}>AI</div>
                <div className={styles.turnContent}>正在思考...</div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <div className={styles.inputRow}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
              placeholder="输入你的回答..."
              className={styles.dialogueInput}
              disabled={dialogueLoading}
            />
            <button onClick={handleSend} className={styles.sendBtn} disabled={dialogueLoading || !input.trim()}>
              {dialogueLoading ? "..." : "发送"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
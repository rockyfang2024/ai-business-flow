// API client for Business Flow Skill Web backend

import type {
  ProcessListItem,
  ProcessInfo,
  DocumentItem,
  ExtractionStatus,
  DialogueTurn,
  KnowledgeDoc,
} from "@/types";

const BASE_URL = "http://localhost:8000/api";

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${path} failed (${res.status}): ${body}`);
  }
  return res.json() as Promise<T>;
}

// ──────────────────────────────────────────────────────────────
// LLM Config (stored in localStorage, passed to backend)
// ──────────────────────────────────────────────────────────────

export interface LLMConfig {
  provider: string;
  model: string;
  apiKey: string;
  baseUrl: string;
}

function getLLMConfig(): LLMConfig {
  try {
    const stored = localStorage.getItem("bfs-llm-config");
    if (stored) return JSON.parse(stored);
  } catch { /* ignore */ }
  return { provider: "openai", model: "gpt-4o", apiKey: "", baseUrl: "https://api.openai.com/v1" };
}

// ──────────────────────────────────────────────────────────────
// Process APIs
// ──────────────────────────────────────────────────────────────

export const api_processes = {
  list: () => api<ProcessListItem[]>("/processes"),

  create: (body: { name: string; description?: string }) =>
    api<ProcessInfo>("/processes", { method: "POST", body: JSON.stringify(body) }),

  get: (processId: string) => api<ProcessInfo>(`/processes/${processId}`),

  getKnowledge: (processId: string) =>
    api<KnowledgeDoc>(`/processes/${processId}/knowledge`),

  delete: (processId: string) => api(`/processes/${processId}`, { method: "DELETE" }),

  listDocuments: (processId: string) => api<DocumentItem[]>(`/processes/${processId}/documents`),

  uploadDocument: (processId: string, filename: string, content: string) =>
    api<{ id: string; filename: string; size: number; path: string }>(
      `/processes/${processId}/documents/upload?filename=${encodeURIComponent(filename)}`,
      { method: "POST", body: content, headers: { "Content-Type": "text/plain" } }
    ),

  uploadDocumentFromPath: (processId: string, path: string) =>
    api<{ id: string; filename: string; size: number; path: string }>(
      `/processes/${processId}/documents/upload-path`,
      { method: "POST", body: JSON.stringify({ path }) }
    ),
};

// ──────────────────────────────────────────────────────────────
// Extraction APIs
// ──────────────────────────────────────────────────────────────

export const api_extraction = {
  getStatus: (processId: string) => api<ExtractionStatus>(`/extraction/${processId}/status`),

  run: (processId: string, documentId?: string) => {
    const cfg = getLLMConfig();
    return api<ExtractionStatus>("/extraction/run", {
      method: "POST",
      body: JSON.stringify({
        process_id: processId,
        document_id: documentId,
        llm_provider: cfg.provider,
        llm_model: cfg.model,
        api_key: cfg.apiKey,
        base_url: cfg.baseUrl,
      }),
    });
  },
};

// ──────────────────────────────────────────────────────────────
// Query APIs
// ──────────────────────────────────────────────────────────────

export const api_query = {
  query: (processId: string, question: string) => {
    const cfg = getLLMConfig();
    return api<{ answer: string; sources: string[]; confidence?: string }>("/query/query", {
      method: "POST",
      body: JSON.stringify({
        process_id: processId,
        question,
        llm_provider: cfg.provider,
        llm_model: cfg.model,
        api_key: cfg.apiKey,
        base_url: cfg.baseUrl,
      }),
    });
  },

  dialogue: (
    processId: string,
    message: string,
    history: DialogueTurn[]
  ) => {
    const cfg = getLLMConfig();
    return api<{ reply: string; is_complete: boolean; extracted_data?: unknown }>("/query/dialogue", {
      method: "POST",
      body: JSON.stringify({
        process_id: processId,
        message,
        history,
        llm_provider: cfg.provider,
        llm_model: cfg.model,
        api_key: cfg.apiKey,
        base_url: cfg.baseUrl,
      }),
    });
  },
};
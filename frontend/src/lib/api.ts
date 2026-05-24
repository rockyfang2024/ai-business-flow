// API client for Business Flow Skill Web backend

import type {
  ProcessListItem,
  ProcessInfo,
  DocumentItem,
  ExtractionStatus,
  DialogueTurn,
  KnowledgeDoc,
} from "@/types";

const BASE_URL = "/api";

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

// ─────────────────────────────────────────────────────────────────────────────
// LLM Config (stored in localStorage, passed to backend)
// ─────────────────────────────────────────────────────────────────────────────

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
  return {
    provider: "openrouter",
    model: "anthropic/claude-sonnet-4.6",
    apiKey: "",
    baseUrl: "https://openrouter.ai/api/v1",
  };
}

function buildLLMBody(extras: Record<string, unknown> = {}) {
  const cfg = getLLMConfig();
  return {
    ...extras,
    llm: {
      provider: cfg.provider,
      model: cfg.model,
      api_key: cfg.apiKey,
      base_url: cfg.baseUrl,
    },
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Process APIs
// ─────────────────────────────────────────────────────────────────────────────

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

// ─────────────────────────────────────────────────────────────────────────────
// Extraction APIs
// ─────────────────────────────────────────────────────────────────────────────

export const api_extraction = {
  getStatus: (processId: string) => api<ExtractionStatus>(`/extraction/${processId}/status`),

  run: (processId: string, documentId?: string) => {
    return api<ExtractionStatus>("/extraction/run", {
      method: "POST",
      body: JSON.stringify(buildLLMBody({ process_id: processId, document_id: documentId })),
    });
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// Query APIs
// ─────────────────────────────────────────────────────────────────────────────

export const api_query = {
  query: (processId: string, question: string) => {
    return api<{ answer: string; sources: string[]; confidence?: string }>("/query/query", {
      method: "POST",
      body: JSON.stringify(buildLLMBody({ process_id: processId, question })),
    });
  },

  dialogue: (
    processId: string,
    message: string,
    history: DialogueTurn[]
  ) => {
    return api<{ reply: string; is_complete: boolean; extracted_data?: unknown }>(
      "/query/dialogue",
      {
        method: "POST",
        body: JSON.stringify(buildLLMBody({ process_id: processId, message, history })),
      }
    );
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// LLM Config API (backend settings)
// ─────────────────────────────────────────────────────────────────────────────

export const api_llm_config = {
  get: () =>
    api<{
      config: Record<string, unknown>;
      available_providers: Array<{
        id: string;
        name: string;
        description: string;
        transport: string;
        auth_type: string;
        env_vars: string[];
        base_url: string;
        is_aggregator: boolean;
        supports_health_check: boolean;
        fallback_models: string[];
      }>;
    }>("/config/llm"),

  update: (body: Record<string, unknown>) =>
    api<{ status: string; config: Record<string, unknown> }>("/config/llm", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  listProviders: () =>
    api<Array<{ id: string; name: string; description: string; transport: string }>>(
      "/config/llm/providers"
    ),

  test: (provider: string, model: string, apiKey?: string, baseUrl?: string) =>
    api<{ status: string; response: string }>("/config/llm/test", {
      method: "POST",
      body: JSON.stringify({ provider, model, api_key: apiKey, base_url: baseUrl }),
    }),
};

export const api_dialogue = {
  getHistory: (processId: string) =>
    api<{ history: DialogueTurn[]; is_complete: boolean }>(
      `/query/dialogue/${processId}/history`
    ),
};
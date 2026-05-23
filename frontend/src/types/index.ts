// Shared TypeScript types for Business Flow Skill Web

export interface ProcessListItem {
  id: string;
  name: string;
  description: string | null;
  updated_at: string;
  has_knowledge: boolean;
}

export interface ProcessInfo extends ProcessListItem {
  created_at: string;
  skill_path: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  size: number;
  uploaded_at: string;
}

export interface ExtractionStatus {
  process_id: string;
  status: "idle" | "running" | "done" | "error";
  progress?: string;
  confidence_report?: string;
  pending_items?: string;
  error?: string;
}

export interface DialogueTurn {
  role: "user" | "assistant";
  content: string;
}

export interface KnowledgeDoc {
  main_yaml: string;
  decision_tree_yaml: string;
  exceptions_yaml: string;
  sla_yaml: string;
  skill_md: string;
  extraction_report?: string;
}

export interface QueryAnswer {
  answer: string;
  sources: string[];
  confidence?: string;
}

export interface DialogueResult {
  reply: string;
  is_complete: boolean;
  extracted_data?: unknown;
}
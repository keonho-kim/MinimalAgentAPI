import type { AgentUiEvent } from "@/lib/stream";

export type ActivityTraceCategory =
  | "search"
  | "list"
  | "command"
  | "file-read"
  | "file-create"
  | "file-edit"
  | "subagent"
  | "skills"
  | "intermediate"
  | "other";

export type ActivityTraceEntry = {
  id: string;
  key: string;
  category: ActivityTraceCategory;
  label: string;
  detail: string;
  status?: string;
  target?: string;
};

export type ActivityEvent = Extract<AgentUiEvent, { kind: "activity" }>;

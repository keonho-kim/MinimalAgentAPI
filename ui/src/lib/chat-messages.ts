import type { ChatMessage } from "@/lib/api";
import {
  activityTraceEntry,
  appendActivityEntry,
  canMergeActivityEntry,
  completeActivityEntries,
} from "@/lib/activity-timeline";
import type { ActivityTraceEntry } from "@/lib/activity-timeline";
import { createId } from "@/lib/id";
import type { FileMentionRange } from "@/lib/file-mentions";
import type { AgentUiEvent } from "@/lib/stream";
import { getSessionHistory } from "@/store/session-store";

export type UiChatMessage = ChatMessage & {
  id: string;
  kind?: "normal" | "reasoning" | "error";
  fileMentions?: FileMentionRange[];
  assistantRunId?: string;
};
export type ActivityBlockMessage = {
  id: string;
  role: "assistant";
  content: "";
  kind: "activity-block";
  entries: ActivityTraceEntry[];
};
export type UiMessage = UiChatMessage | ActivityBlockMessage;

export function hydrateSessionMessages(
  userId: string,
  sessionUuid: string,
): UiMessage[] {
  return getSessionHistory(userId, sessionUuid).map((item) => ({
    ...item,
    id: createId(),
  }));
}

export function userMessage(
  content: string,
  fileMentions: FileMentionRange[] = [],
): UiMessage {
  return {
    id: createId(),
    role: "user",
    content,
    fileMentions: fileMentions.length ? fileMentions : undefined,
  };
}

export function errorMessage(content: string): UiMessage {
  return {
    id: createId(),
    role: "assistant",
    content,
    kind: "error",
  };
}

export function appendAgentUiEvent(
  messages: UiMessage[],
  event: AgentUiEvent,
  scopeId: string,
): UiMessage[] {
  if (event.kind === "assistant_delta" && event.text) {
    return appendAssistantText(messages, event);
  }

  if (event.kind === "think_delta" && event.text) {
    return [
      ...messages,
      {
        id: createId(),
        role: "assistant",
        content: event.text,
        kind: "reasoning",
      },
    ];
  }

  if (event.kind !== "activity") {
    return messages;
  }

  const entry = activityTraceEntry(event);
  return entry ? appendActivityBlock(messages, entry, scopeId) : messages;
}

export function completeActivityBlocks(messages: UiMessage[]): UiMessage[] {
  return messages.map((item) =>
    item.kind === "activity-block"
      ? { ...item, entries: completeActivityEntries(item.entries) }
      : item,
  );
}

function appendAssistantText(
  messages: UiMessage[],
  event: Extract<AgentUiEvent, { kind: "assistant_delta" | "think_delta" }>,
): UiMessage[] {
  const next = [...messages];
  const last = next.at(-1);
  const runId = event.runId;
  const text = event.text ?? "";

  if (
    last?.role === "assistant" &&
    last.kind === "normal" &&
    (!runId || last.assistantRunId === runId)
  ) {
    next[next.length - 1] = {
      ...last,
      content: `${last.content}${text}`,
      assistantRunId: last.assistantRunId ?? runId,
    };
    return next;
  }

  return [
    ...next,
    {
      id: createId(),
      role: "assistant",
      content: text,
      kind: "normal",
      assistantRunId: runId,
    },
  ];
}

function appendActivityBlock(
  messages: UiMessage[],
  entry: ActivityTraceEntry,
  scopeId: string,
): UiMessage[] {
  const next = [...messages];
  const existingIndex = findLastIndex(
    next,
    (item) =>
      item.kind === "activity-block" && canMergeActivityEntry(item.entries, entry),
  );

  if (existingIndex !== -1) {
    const existing = next[existingIndex] as ActivityBlockMessage;
    next[existingIndex] = {
      ...existing,
      entries: appendActivityEntry(existing.entries, entry),
    };
    return next;
  }

  const last = next.at(-1);
  if (last?.kind === "activity-block") {
    next[next.length - 1] = {
      ...last,
      entries: appendActivityEntry(last.entries, entry),
    };
    return next;
  }

  const block: ActivityBlockMessage = {
    id: `activity-block:${scopeId}:${createId()}`,
    role: "assistant",
    content: "",
    kind: "activity-block",
    entries: [entry],
  };
  return [...next, block];
}

function findLastIndex<T>(values: T[], predicate: (value: T) => boolean) {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    if (predicate(values[index])) {
      return index;
    }
  }
  return -1;
}

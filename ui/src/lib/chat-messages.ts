import type { ChatMessage } from "@/lib/api";
import {
  activityMessageId,
  mergeActivityEvent,
  normalizeGroupedActivity,
} from "@/lib/activity-grouping";
import { createId } from "@/lib/id";
import type { FileMentionRange } from "@/lib/file-mentions";
import type { AgentUiEvent } from "@/lib/stream";
import { getSessionHistory } from "@/store/session-store";

export type UiMessage = ChatMessage & {
  id: string;
  kind?: "normal" | "reasoning" | "activity" | "error";
  activity?: Extract<AgentUiEvent, { kind: "activity" }>;
  fileMentions?: FileMentionRange[];
};

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
    return appendAssistantText(messages, event.text);
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

  const activity = normalizeGroupedActivity(event);
  const activityId = activityMessageId(activity, createId(), scopeId);
  const nextMessage: UiMessage = {
    id: activityId,
    role: "assistant",
    content: activity.message || activity.label || activity.name || "Agent activity",
    kind: "activity",
    activity,
  };
  const existingIndex = messages.findIndex((item) => item.id === activityId);
  if (existingIndex === -1) {
    return [...messages, nextMessage];
  }

  const next = [...messages];
  const existing = next[existingIndex];
  const mergedActivity = existing.activity
    ? mergeActivityEvent(existing.activity, activity)
    : activity;
  next[existingIndex] = {
    ...nextMessage,
    content:
      mergedActivity.message ||
      mergedActivity.label ||
      mergedActivity.name ||
      nextMessage.content,
    activity: mergedActivity,
  };
  return next;
}

function appendAssistantText(messages: UiMessage[], text: string): UiMessage[] {
  const next = [...messages];
  const last = next.at(-1);

  if (last?.role === "assistant" && last.kind === "normal") {
    next[next.length - 1] = {
      ...last,
      content: `${last.content}${text}`,
    };
    return next;
  }

  return [
    ...next,
    { id: createId(), role: "assistant", content: text, kind: "normal" },
  ];
}

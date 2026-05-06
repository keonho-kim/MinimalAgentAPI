import type { AgentUiEvent } from "@/lib/stream";

export type ActivityEvent = Extract<AgentUiEvent, { kind: "activity" }>;

const HITL_TOOL_NAMES = new Set([
  "write_file",
  "edit_file",
  "edit_docx",
  "edit_hwpx",
  "edit_pptx",
  "edit_xlsx",
]);

export function activityMessageId(
  event: ActivityEvent,
  fallbackId: string,
  scopeId: string,
) {
  const groupKey = activityGroupKey(event);
  if (groupKey) {
    return `activity-group:${scopeId}:${groupKey}`;
  }
  return event.id ? `activity:${event.id}` : fallbackId;
}

export function mergeActivityEvent(
  previous: ActivityEvent,
  incoming: ActivityEvent,
): ActivityEvent {
  const normalized = normalizeGroupedActivity(incoming);
  const previousSummary = objectSummary(previous.summary);
  const nextSummary = objectSummary(normalized.summary);
  const previousRunKey = activityRunKey(previous);
  const runKey = activityRunKey(normalized);
  const groupedRunIds = new Set(stringArray(previousSummary._groupedRunIds));
  const activeRunIds = new Set(stringArray(previousSummary._activeRunIds));

  if (previousRunKey) {
    groupedRunIds.add(previousRunKey);
    if (previous.status === "pending" || previous.status === "running") {
      activeRunIds.add(previousRunKey);
    }
  }

  if (runKey) {
    groupedRunIds.add(runKey);
    if (normalized.status === "pending" || normalized.status === "running") {
      activeRunIds.add(runKey);
    } else if (normalized.status === "completed" || normalized.status === "error") {
      activeRunIds.delete(runKey);
    }
  }

  const groupedCount = Math.max(
    groupedRunIds.size,
    numberValue(previousSummary.groupedCount) ?? 1,
  );
  const status = mergeStatus(previous.status, normalized.status, activeRunIds.size);

  return {
    ...previous,
    ...normalized,
    status,
    summary: {
      ...previousSummary,
      ...nextSummary,
      groupedCount,
      _groupedRunIds: [...groupedRunIds],
      _activeRunIds: [...activeRunIds],
    },
  };
}

export function normalizeGroupedActivity(event: ActivityEvent): ActivityEvent {
  const groupKey = activityGroupKey(event);
  if (groupKey !== "skills-check") {
    return event;
  }

  const summary = objectSummary(event.summary);
  return {
    ...event,
    label: "스킬 확인",
    message: skillCheckMessage(event.status),
    summary: {
      ...summary,
      path: null,
      result: null,
      description: null,
    },
  };
}

export function activityGroupKey(event: ActivityEvent) {
  const summary = objectSummary(event.summary);
  if (isApprovalActivity(event, summary)) {
    return null;
  }

  const skillName = stringValue(summary.skillName);
  if (skillName) {
    return `skill-read:${skillName}`;
  }

  if (isSkillCheckActivity(event, summary)) {
    return "skills-check";
  }

  if (event.name === "ls") {
    const path = stringValue(summary.path);
    return path ? `ls:${path}` : null;
  }

  return null;
}

function mergeStatus(
  previousStatus: string | undefined,
  nextStatus: string | undefined,
  activeCount: number,
) {
  if (previousStatus === "error" || nextStatus === "error") {
    return "error";
  }
  if (activeCount > 0) {
    return nextStatus === "pending" ? "pending" : "running";
  }
  return nextStatus ?? previousStatus;
}

function isApprovalActivity(
  event: ActivityEvent,
  summary: Record<string, unknown>,
) {
  return summary.requiresApproval === true || HITL_TOOL_NAMES.has(event.name ?? "");
}

function isSkillCheckActivity(
  event: ActivityEvent,
  summary: Record<string, unknown>,
) {
  const name = event.name ?? "";
  if (
    name === "workspace_skills" ||
    name === "SkillsMiddleware" ||
    name.startsWith("SkillsMiddleware.")
  ) {
    return true;
  }

  if (Array.isArray(summary.skills)) {
    return true;
  }

  return event.name === "ls" && looksLikeAgentsPath(summary);
}

function looksLikeAgentsPath(summary: Record<string, unknown>) {
  const values = [
    stringValue(summary.path),
    stringValue(summary.result),
    stringValue(summary.description),
  ];
  return values.some((value) => value?.includes("/.agents"));
}

function activityRunKey(event: ActivityEvent) {
  return (
    event.runId ||
    event.id ||
    `${event.name ?? "activity"}:${event.status ?? "unknown"}`
  );
}

function skillCheckMessage(status: string | undefined) {
  if (status === "pending") {
    return "AGENT가 workspace 스킬 확인을 준비합니다.";
  }
  if (status === "running") {
    return "AGENT가 workspace 스킬을 확인합니다.";
  }
  if (status === "error") {
    return "AGENT가 workspace 스킬 확인 중 오류가 발생했습니다.";
  }
  return "AGENT가 workspace 스킬 확인을 완료했습니다.";
}

function objectSummary(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}

function numberValue(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringArray(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

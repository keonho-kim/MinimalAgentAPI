import type { AgentUiEvent } from "@/lib/stream";

export type ActivityEvent = Extract<AgentUiEvent, { kind: "activity" }>;
type ActivityStep = {
  id: string;
  name?: string;
  label?: string;
  message?: string;
  status?: string;
};

const HITL_TOOL_NAMES = new Set([
  "write_file",
  "edit_file",
  "edit_docx",
  "edit_hwpx",
  "edit_pptx",
  "edit_xlsx",
]);

const READ_WORKFLOW_FILE_TYPES = new Set(["docx", "hwpx", "pdf", "pptx", "xlsx"]);
const READ_TOOL_FILE_TYPES: Record<string, string> = {
  answer_docx_question: "docx",
  answer_hwpx_question: "hwpx",
  answer_pdf_question: "pdf",
  answer_pptx_question: "pptx",
  answer_xlsx_question: "xlsx",
};
const LEGACY_AGENT_STEP_NAMES = new Set([
  "office_file_agent",
  "agent_hwpx",
  "agent_docx",
  "agent_pptx",
  "agent_xlsx",
  "agent_pdf",
  "answer_hwpx_question",
  "answer_docx_question",
  "answer_pptx_question",
  "answer_xlsx_question",
  "answer_pdf_question",
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
  const intermediateTexts = mergeIntermediateTexts(previousSummary, nextSummary);
  const activitySteps = mergeActivitySteps(previousSummary, nextSummary, normalized);
  const mergesAgentStep = isAgentStep(normalized);
  const exposesGroupedCount = !isSubagentActivity(previous) && !mergesAgentStep;
  const summary = {
    ...(mergesAgentStep ? previousSummary : { ...previousSummary, ...nextSummary }),
    _groupedRunIds: [...groupedRunIds],
    _activeRunIds: [...activeRunIds],
    ...(exposesGroupedCount ? { groupedCount } : {}),
    ...(intermediateTexts.length ? { intermediateTexts } : {}),
    ...(activitySteps.length ? { activitySteps } : {}),
  };

  if (!exposesGroupedCount) {
    delete summary.groupedCount;
  }

  return {
    ...previous,
    ...(mergesAgentStep ? {} : normalized),
    status,
    summary,
  };
}

export function normalizeGroupedActivity(event: ActivityEvent): ActivityEvent {
  const groupKey = activityGroupKey(event);
  if (groupKey?.startsWith("file-read:")) {
    return normalizeFileReadActivity(event);
  }

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

  if (isSubagentActivity(event)) {
    const runId = event.runId || event.id;
    return runId ? `subagent:${runId}` : null;
  }

  if (isAgentStep(event)) {
    const delegationRunId =
      stringValue(summary.delegationRunId) || legacyDelegationRunId(event);
    return delegationRunId ? `subagent:${delegationRunId}` : null;
  }

  const skillName = stringValue(summary.skillName);
  if (skillName) {
    return `skill-read:${skillName}`;
  }

  if (isSkillCheckActivity(event, summary)) {
    return "skills-check";
  }

  const fileReadKey = fileReadGroupKey(event, summary);
  if (fileReadKey) {
    return fileReadKey;
  }

  if (event.type === "model") {
    return "model-response";
  }

  if (event.type === "model_output") {
    return "intermediate-model-output";
  }

  if (event.name === "ls") {
    const path = stringValue(summary.path);
    return path ? `ls:${path}` : null;
  }

  if (event.type === "tool" && event.name) {
    const target =
      stringValue(summary.fileId) ||
      stringValue(summary.path) ||
      stringValue(summary.filename) ||
      "general";
    return `tool:${event.name}:${target}`;
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
  const summary = objectSummary(event.summary);
  const fileReadKey = fileReadGroupKey(event, summary);
  if (fileReadKey) {
    return fileReadKey;
  }

  return (
    event.runId ||
    event.id ||
    `${event.name ?? "activity"}:${event.status ?? "unknown"}`
  );
}

function fileReadGroupKey(
  event: ActivityEvent,
  summary: Record<string, unknown>,
) {
  const fileType = readFileType(event, summary);
  if (!fileType) {
    return null;
  }

  const target =
    stringValue(summary.fileId) ||
    stringValue(summary.path) ||
    stringValue(summary.filename);
  if (!target) {
    return null;
  }

  return `file-read:${fileType}:${normalizeTarget(target)}`;
}

function readFileType(
  event: ActivityEvent,
  summary: Record<string, unknown>,
) {
  const summaryType = stringValue(summary.fileType);
  if (summaryType && READ_WORKFLOW_FILE_TYPES.has(summaryType)) {
    return summaryType;
  }

  if (event.type === "tool" && event.name) {
    return READ_TOOL_FILE_TYPES[event.name] ?? null;
  }

  if (event.type !== "workflow" || !event.name) {
    return null;
  }

  const match = /^([a-z0-9]+)_read_[a-z0-9_]+$/.exec(event.name);
  const fileType = match?.[1];
  return fileType && READ_WORKFLOW_FILE_TYPES.has(fileType) ? fileType : null;
}

function normalizeFileReadActivity(event: ActivityEvent): ActivityEvent {
  const summary = objectSummary(event.summary);
  const fileType = readFileType(event, summary);
  if (!fileType) {
    return event;
  }

  const label = `${fileType.toUpperCase()} 읽기`;
  if (event.type === "workflow") {
    return {
      ...event,
      label,
    };
  }

  return {
    ...event,
    label,
    message: fileReadMessage(fileType, event.status),
    summary: {
      ...summary,
      operation: "read",
      fileType,
    },
  };
}

function fileReadMessage(fileType: string, status: string | undefined) {
  const label = fileType.toUpperCase();
  if (status === "pending") {
    return `${label} 파일 읽기를 준비합니다.`;
  }
  if (status === "running") {
    return `${label} 파일 읽기를 시작합니다.`;
  }
  if (status === "error") {
    return `${label} 파일 읽기 중 오류가 발생했습니다.`;
  }
  return `${label} 파일 읽기를 완료했습니다.`;
}

function normalizeTarget(value: string) {
  return value.trim().replace(/^\/+/, "");
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

function mergeIntermediateTexts(
  previousSummary: Record<string, unknown>,
  nextSummary: Record<string, unknown>,
) {
  return uniqueStrings([
    ...stringArray(previousSummary.intermediateTexts),
    ...singleStringArray(previousSummary.intermediateText),
    ...stringArray(nextSummary.intermediateTexts),
    ...singleStringArray(nextSummary.intermediateText),
  ]).slice(-10);
}

function mergeActivitySteps(
  previousSummary: Record<string, unknown>,
  nextSummary: Record<string, unknown>,
  incoming: ActivityEvent,
) {
  const steps = activityStepArray(previousSummary.activitySteps);
  const incomingSteps = [
    ...activityStepArray(nextSummary.activitySteps),
    ...singleActivityStep(incoming),
  ];

  for (const step of incomingSteps) {
    const index = steps.findIndex((item) => item.id === step.id);
    if (index === -1) {
      steps.push(step);
    } else {
      steps[index] = { ...steps[index], ...step };
    }
  }

  return steps.slice(-12);
}

function singleActivityStep(event: ActivityEvent) {
  if (!isAgentStep(event)) {
    return [];
  }

  const id = event.runId || event.id || event.name;
  if (!id) {
    return [];
  }

  return [
    {
      id,
      name: event.name,
      label: event.label,
      message: event.message,
      status: event.status,
    },
  ];
}

function activityStepArray(value: unknown): ActivityStep[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is ActivityStep => {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      return false;
    }
    const record = item as Record<string, unknown>;
    return typeof record.id === "string" && record.id.trim().length > 0;
  });
}

function isSubagentActivity(event: ActivityEvent) {
  return event.type === "subagent" || isLegacySubagentActivity(event);
}

function isAgentStep(event: ActivityEvent) {
  return event.type === "agent_step" || isLegacyAgentStepActivity(event);
}

function isLegacySubagentActivity(event: ActivityEvent) {
  return event.type === "chain" && event.name === "task";
}

function isLegacyAgentStepActivity(event: ActivityEvent) {
  return event.type === "chain" && LEGACY_AGENT_STEP_NAMES.has(event.name ?? "");
}

function legacyDelegationRunId(event: ActivityEvent) {
  if (!isLegacyAgentStepActivity(event)) {
    return null;
  }

  const parentIds = stringArray(event.parentIds);
  if (parentIds.length > 1) {
    return parentIds[1];
  }
  return parentIds[0] ?? null;
}

function singleStringArray(value: unknown) {
  const string = stringValue(value);
  return string ? [string] : [];
}

function uniqueStrings(values: string[]) {
  return [...new Set(values)];
}

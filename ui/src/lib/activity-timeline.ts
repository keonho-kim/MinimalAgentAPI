import type {
  ActivityEvent,
  ActivityTraceCategory,
  ActivityTraceEntry,
} from "./activity-timeline-types";

export {
  activityTimelineSummary,
  completeActivityEntries,
  hasRunningActivity,
} from "./activity-timeline-summary";
export type {
  ActivityTraceCategory,
  ActivityTraceEntry,
} from "./activity-timeline-types";

const READ_TOOL_NAMES = new Set([
  "read_file",
  "read_docx_file",
  "read_hwpx_file",
  "read_pdf_file",
  "read_pptx_file",
  "read_xlsx_file",
]);
const EDIT_TOOL_NAMES = new Set([
  "edit_file",
  "edit_docx",
  "edit_hwpx",
  "edit_pptx",
  "edit_xlsx",
]);

export function activityTraceEntry(event: ActivityEvent): ActivityTraceEntry | null {
  if (event.type === "model") {
    return null;
  }

  const details = objectDetails(event.details);
  if (event.type === "model_output") {
    const detail = intermediateDetail(details);
    return detail
      ? entry(event, "intermediate", "중간 응답", detail, detail)
      : null;
  }

  const category = activityCategory(event, details);
  const target = activityTarget(event, details);
  const label = activityLabel(event, category);
  const detail = activityDetail(event, category, target);
  const key = activityKey(event, category, target, details);
  const id = activityId(event, key);

  return {
    id,
    key,
    category,
    label,
    detail,
    status: event.status,
    target: target ?? undefined,
  };
}

export function appendActivityEntry(
  entries: ActivityTraceEntry[],
  incoming: ActivityTraceEntry,
) {
  const next = [...entries];
  const index = activityEntryIndex(next, incoming);
  if (index === -1) {
    next.push(uniqueActivityEntry(next, incoming));
    return next.slice(-40);
  }

  next[index] = mergeActivityEntry(next[index], incoming);
  return next.slice(-40);
}

export function canMergeActivityEntry(
  entries: ActivityTraceEntry[],
  incoming: ActivityTraceEntry,
) {
  return activityEntryIndex(entries, incoming) !== -1;
}

function activityCategory(
  event: ActivityEvent,
  details: Record<string, unknown>,
): ActivityTraceCategory {
  const name = event.name ?? "";
  if (isSkillsActivity(event, details)) {
    return "skills";
  }
  if (isSubagentActivity(event)) {
    return "subagent";
  }
  if (name === "grep" || name === "glob") {
    return "search";
  }
  if (name === "ls") {
    return "list";
  }
  if (name === "execute") {
    return "command";
  }
  if (name === "write_file") {
    return "file-create";
  }
  if (EDIT_TOOL_NAMES.has(name) || name.startsWith("edit_")) {
    return "file-edit";
  }
  if (READ_TOOL_NAMES.has(name) || /^read_[a-z0-9]+_file$/.test(name)) {
    return "file-read";
  }
  return "other";
}

function activityTarget(event: ActivityEvent, details: Record<string, unknown>) {
  if (event.name === "grep") {
    return stringValue(details.query) || stringValue(details.pattern);
  }
  if (event.name === "execute") {
    return (
      stringValue(details.command) ||
      stringValue(details.description) ||
      stringValue(details.result)
    );
  }
  return (
    editedFileTarget(details.editedFile) ||
    stringValue(details.filename) ||
    stringValue(details.path) ||
    stringValue(details.fileId) ||
    stringValue(details.query) ||
    stringValue(details.description)
  );
}

function activityLabel(event: ActivityEvent, category: ActivityTraceCategory) {
  if (category === "subagent") {
    return "서브에이전트 위임";
  }
  if (category === "skills") {
    return "스킬 확인";
  }
  return event.label || event.name || "작업";
}

function activityDetail(
  event: ActivityEvent,
  category: ActivityTraceCategory,
  target: string | null,
) {
  const targetLabel = target ? displayTarget(target) : null;
  if (category === "search") {
    return targetLabel ? `Searched for ${targetLabel}` : fallbackDetail(event);
  }
  if (category === "list") {
    return targetLabel ? `Listed files in ${targetLabel}` : fallbackDetail(event);
  }
  if (category === "command") {
    return targetLabel ? `${targetLabel} 실행함` : fallbackDetail(event);
  }
  if (category === "file-read") {
    return targetLabel ? `Read ${basename(targetLabel)}` : fallbackDetail(event);
  }
  if (category === "file-create") {
    return targetLabel ? `Created ${basename(targetLabel)}` : fallbackDetail(event);
  }
  if (category === "file-edit") {
    return targetLabel ? `Edited ${basename(targetLabel)}` : fallbackDetail(event);
  }
  if (category === "subagent") {
    return targetLabel ? `Delegated to ${targetLabel}` : fallbackDetail(event);
  }
  if (category === "skills") {
    return targetLabel ? `Checked ${targetLabel}` : fallbackDetail(event);
  }
  return fallbackDetail(event);
}

function activityKey(
  event: ActivityEvent,
  category: ActivityTraceCategory,
  target: string | null,
  details: Record<string, unknown>,
) {
  if (category === "subagent") {
    return [
      "subagent",
      stringValue(details.delegationRunId) ||
        legacyDelegationRunId(event) ||
        stringValue(details.agentName) ||
        target ||
        "task",
    ].join(":");
  }
  if (target) {
    return [category, event.name ?? "activity", target].join(":");
  }
  return [category, event.name ?? "activity", event.runId || event.id || "general"].join(
    ":",
  );
}

function activityId(event: ActivityEvent, key: string) {
  return event.runId || event.id || key;
}

function activityEntryIndex(
  entries: ActivityTraceEntry[],
  incoming: ActivityTraceEntry,
) {
  const openIndex = findLastIndex(
    entries,
    (entry) => entry.key === incoming.key && !isTerminalStatus(entry.status),
  );
  if (openIndex !== -1) {
    return openIndex;
  }

  const exactIndex = findLastIndex(entries, (entry) => entry.id === incoming.id);
  if (exactIndex !== -1 && !startsNewEntry(entries[exactIndex], incoming)) {
    return exactIndex;
  }

  const latestKeyIndex = findLastIndex(
    entries,
    (entry) => entry.key === incoming.key,
  );
  if (
    latestKeyIndex !== -1 &&
    !startsNewEntry(entries[latestKeyIndex], incoming)
  ) {
    return latestKeyIndex;
  }

  return -1;
}

function startsNewEntry(
  existing: ActivityTraceEntry,
  incoming: ActivityTraceEntry,
) {
  return (
    isTerminalStatus(existing.status) &&
    (incoming.status === "pending" || incoming.status === "running")
  );
}

function mergeActivityEntry(
  existing: ActivityTraceEntry,
  incoming: ActivityTraceEntry,
) {
  const incomingRank = statusRank(incoming.status);
  const existingRank = statusRank(existing.status);
  const base = incomingRank >= existingRank ? existing : incoming;
  const update = incomingRank >= existingRank ? incoming : existing;

  return {
    ...base,
    ...definedValues(update),
  };
}

function uniqueActivityEntry(
  entries: ActivityTraceEntry[],
  incoming: ActivityTraceEntry,
) {
  if (!entries.some((entry) => entry.id === incoming.id)) {
    return incoming;
  }

  let index = 2;
  let id = `${incoming.id}:${index}`;
  while (entries.some((entry) => entry.id === id)) {
    index += 1;
    id = `${incoming.id}:${index}`;
  }

  return { ...incoming, id };
}

function entry(
  event: ActivityEvent,
  category: ActivityTraceCategory,
  label: string,
  detail: string,
  target: string,
) {
  const key = [category, event.runId || event.id || target].join(":");
  return {
    id: activityId(event, key),
    key,
    category,
    label,
    detail,
    status: event.status,
    target,
  };
}

function intermediateDetail(details: Record<string, unknown>) {
  const text =
    stringValue(details.intermediateText) ||
    stringArray(details.intermediateTexts).join("\n\n");
  return text || null;
}

function isSkillsActivity(
  event: ActivityEvent,
  details: Record<string, unknown>,
) {
  const name = event.name ?? "";
  return (
    name === "workspace_skills" ||
    name === "SkillsMiddleware" ||
    name.startsWith("SkillsMiddleware.") ||
    Array.isArray(details.skills) ||
    stringValue(details.skillName) !== null
  );
}

function isSubagentActivity(event: ActivityEvent) {
  return (
    event.type === "subagent" ||
    event.type === "agent_step" ||
    event.name === "task" ||
    (event.type === "chain" && event.name === "task") ||
    (event.type === "chain" && (event.name ?? "").startsWith("agent_"))
  );
}

function legacyDelegationRunId(event: ActivityEvent) {
  const parentIds = Array.isArray(event.parentIds)
    ? event.parentIds.filter((item): item is string => typeof item === "string")
    : [];
  return parentIds[1] ?? parentIds[0] ?? null;
}

function fallbackDetail(event: ActivityEvent) {
  return event.message || event.label || event.name || "Agent activity";
}

function objectDetails(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function editedFileTarget(value: unknown) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const record = value as Record<string, unknown>;
  return stringValue(record.filename) || stringValue(record.path);
}

function stringValue(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function stringArray(value: unknown) {
  return Array.isArray(value)
    ? value.filter(
        (item): item is string =>
          typeof item === "string" && Boolean(item.trim()),
      )
    : [];
}

function basename(value: string) {
  return value.split("/").filter(Boolean).at(-1) ?? value;
}

function displayTarget(value: string) {
  return value.trim().replace(/^\/+/, "") || value;
}

function definedValues(entry: ActivityTraceEntry) {
  return Object.fromEntries(
    Object.entries(entry).filter(([, value]) => value !== undefined),
  ) as Partial<ActivityTraceEntry>;
}

function findLastIndex<T>(values: T[], predicate: (value: T) => boolean) {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    if (predicate(values[index])) {
      return index;
    }
  }
  return -1;
}

function isTerminalStatus(status: string | undefined) {
  return status === "completed" || status === "error";
}

function statusRank(status: string | undefined) {
  if (status === "error") {
    return 4;
  }
  if (status === "completed") {
    return 3;
  }
  if (status === "running") {
    return 2;
  }
  if (status === "pending") {
    return 1;
  }
  return 0;
}

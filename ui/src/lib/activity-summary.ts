export function activityDetailLines(summary: Record<string, unknown>) {
  const skillName = stringValue(summary.skillName);
  if (skillName) {
    return [skillName];
  }

  const skills = summary.skills;
  if (Array.isArray(skills)) {
    const names = skills.filter(
      (skill): skill is string =>
        typeof skill === "string" && skill.trim().length > 0,
    );
    return names.slice(0, 4);
  }

  const lines = [
    stringValue(summary.path),
    stringValue(summary.filename),
    stringValue(summary.description),
    pageCountLine(summary.pageCount),
    relevantPagesLine(summary.relevantPages),
    editedFileLine(summary.editedFile),
    stringValue(summary.result),
  ].filter(
    (line): line is string =>
      typeof line === "string" && !looksLikeRawRuntimeValue(line),
  );

  return unique(lines).slice(0, 4);
}

function stringValue(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return null;
}

function pageCountLine(value: unknown): string | null {
  return typeof value === "number" && Number.isFinite(value)
    ? `${value} pages`
    : null;
}

function relevantPagesLine(value: unknown): string | null {
  if (!Array.isArray(value) || !value.length) {
    return null;
  }
  const pages = value
    .filter((item): item is number => typeof item === "number")
    .slice(0, 8);
  return pages.length ? `relevant pages: ${pages.join(", ")}` : null;
}

function editedFileLine(value: unknown): string | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  const record = value as Record<string, unknown>;
  return stringValue(record.filename) || stringValue(record.path);
}

function looksLikeRawRuntimeValue(value: string) {
  const trimmed = value.trim();
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    return true;
  }
  return [
    "Command(",
    "ToolMessage(",
    "AIMessage(",
    "tool_call_id=",
    "additional_kwargs=",
    "response_metadata=",
  ].some((marker) => value.includes(marker));
}

function unique(values: string[]) {
  return [...new Set(values)];
}

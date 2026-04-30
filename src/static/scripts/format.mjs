export function shouldRenderActivity(activity) {
  return ["running", "completed", "error"].includes(activity.status);
}

export function activityRenderKey(activity) {
  return `${activity.id || activity.name || "activity"}:${activity.status || "unknown"}`;
}

export function activityTitleText(activity) {
  if (activity.message) {
    return activity.message;
  }

  const label = activity.label || activity.name || "작업";

  if (activity.status === "running") {
    return `AGENT가 ${label} 작업을 시작합니다.`;
  }

  if (activity.status === "completed") {
    return `AGENT가 ${label} 작업을 완료했습니다.`;
  }

  if (activity.status === "error") {
    return `AGENT가 ${label} 작업 중 오류가 발생했습니다.`;
  }

  return `AGENT가 ${label} 작업을 준비합니다.`;
}

export function activityStatusText(status) {
  if (status === "completed") {
    return "done";
  }

  if (status === "error") {
    return "error";
  }

  return "running";
}

export function activityPath(activity) {
  const summary = activity.summary || {};
  const source = activity.input || activity.output || {};

  if (summary.path) {
    return summary.path;
  }

  if (typeof source !== "object" || source === null) {
    return "";
  }

  return source.file_path || source.path || "";
}

export function formatActivitySummary(summary = {}) {
  const lines = [];

  for (const [label, value] of [
    ["path", summary.path],
    ["command", summary.command],
    ["query", summary.query],
    ["description", summary.description],
    ["result", summary.result],
  ]) {
    if (value !== undefined && value !== null && value !== "") {
      lines.push(`${label}: ${value}`);
    }
  }

  return lines.join("\n");
}

export function fileMetaText(file) {
  const parts = [];
  if (file.type) {
    parts.push(file.type);
  }
  if (typeof file.size === "number") {
    parts.push(formatBytes(file.size));
  }
  if (typeof file.modified_at === "number") {
    parts.push(new Date(file.modified_at * 1000).toLocaleString());
  }
  return parts.join(" · ");
}

function formatBytes(size) {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

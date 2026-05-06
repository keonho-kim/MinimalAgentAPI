import type { HitlActionRequest } from "@/lib/api";

export function formatActionTarget(action: HitlActionRequest) {
  const path = stringArg(action.args, "file_path") ?? stringArg(action.args, "path");
  return path ?? "대상 파일 정보 없음";
}

export function stringArg(args: Record<string, unknown>, key: string) {
  const value = args[key];
  return typeof value === "string" && value.trim() ? value : null;
}

export function formatActionName(name: string) {
  if (name === "write_file") {
    return "파일 작성";
  }
  if (name === "edit_file") {
    return "파일 수정";
  }
  if (name === "edit_docx") {
    return "DOCX 파일 수정";
  }
  if (name === "edit_hwpx") {
    return "HWPX 파일 수정";
  }
  if (name === "edit_pptx") {
    return "PPTX 파일 수정";
  }
  if (name === "edit_xlsx") {
    return "XLSX 파일 수정";
  }
  return name.replaceAll("_", " ");
}

export function actionSummary(action: HitlActionRequest) {
  const target = formatActionTarget(action);
  if (action.name === "write_file") {
    return {
      description: `${target} 파일을 새로 작성하거나 덮어씁니다.`,
      change: summarizeText(stringArg(action.args, "content"), "파일 내용을 저장합니다."),
    };
  }
  if (action.name === "edit_file") {
    return {
      description: `${target} 파일의 내용을 수정합니다.`,
      change:
        stringArg(action.args, "instruction") ??
        summarizeReplace(action.args) ??
        "요청한 내용에 맞게 파일을 수정합니다.",
    };
  }
  if (isOfficeEditTool(action.name)) {
    return {
      description: `${target} 문서를 수정합니다.`,
      change:
        stringArg(action.args, "instruction") ??
        "문서 편집 workflow를 실행해 수정본을 생성합니다.",
    };
  }
  return {
    description: `${target}에 대해 ${formatActionName(action.name)} 작업을 실행합니다.`,
    change:
      compactKeyValues(action.args)
        .map(([key, value]) => `${humanizeKey(key)}: ${value}`)
        .join("\n") || "작업 요청 값을 유지합니다.",
  };
}

export function replaceArg(args: Record<string, unknown>, direction: "old" | "new") {
  const candidates =
    direction === "old"
      ? ["old_text", "OLD_TEXT", "old_string", "old_str"]
      : ["new_text", "NEW_TEXT", "new_string", "new_str"];
  for (const key of candidates) {
    const value = stringArg(args, key);
    if (value) {
      return value;
    }
  }
  return null;
}

export function compactKeyValues(args: Record<string, unknown>) {
  return Object.entries(args)
    .filter(([key, value]) => {
      return (
        !["content", "path", "file_path", "instruction"].includes(key) &&
        (typeof value === "string" ||
          typeof value === "number" ||
          typeof value === "boolean")
      );
    })
    .map(([key, value]) => [key, summarizeText(String(value), "")] as const)
    .filter(([, value]) => value);
}

export function humanizeKey(key: string) {
  return key
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

export function shouldShowContentEditor(action: HitlActionRequest) {
  return action.name === "write_file" || "content" in action.args;
}

export function shouldShowInstructionEditor(action: HitlActionRequest) {
  return isOfficeEditTool(action.name) || "instruction" in action.args;
}

function summarizeReplace(args: Record<string, unknown>) {
  const oldText = replaceArg(args, "old");
  const newText = replaceArg(args, "new");
  if (oldText && newText) {
    return `"${oldText}" 내용을 "${newText}"로 바꿉니다.`;
  }
  return null;
}

function summarizeText(value: string | null, fallback: string) {
  if (!value) {
    return fallback;
  }
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > 160 ? `${normalized.slice(0, 160)}...` : normalized;
}

function isOfficeEditTool(name: string) {
  return ["edit_docx", "edit_hwpx", "edit_pptx", "edit_xlsx"].includes(name);
}

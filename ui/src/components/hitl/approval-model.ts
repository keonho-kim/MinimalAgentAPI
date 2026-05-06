import type { HitlActionRequest } from "@/lib/api";

export type HitlMode = "review" | "edit" | "reject";
export type HitlDraft = {
  path: string;
  content: string;
  instruction: string;
};

export function actionToDraft(action: HitlActionRequest): HitlDraft {
  return {
    path: stringArg(action.args, "file_path") ?? stringArg(action.args, "path") ?? "",
    content: stringArg(action.args, "content") ?? "",
    instruction: stringArg(action.args, "instruction") ?? "",
  };
}

export function mergeDraftArgs(action: HitlActionRequest, draft: HitlDraft) {
  const args = { ...(action.args ?? {}) };
  if ("file_path" in args) {
    args.file_path = draft.path;
  } else if ("path" in args) {
    args.path = draft.path;
  } else if (draft.path.trim()) {
    args.path = draft.path;
  }

  if ("content" in args || action.name === "write_file") {
    args.content = draft.content;
  }
  if ("instruction" in args || isOfficeEditTool(action.name)) {
    args.instruction = draft.instruction;
  }
  return args;
}

function stringArg(args: Record<string, unknown>, key: string) {
  const value = args[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function isOfficeEditTool(name: string) {
  return ["edit_docx", "edit_hwpx", "edit_pptx", "edit_xlsx"].includes(name);
}

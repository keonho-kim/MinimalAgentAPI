import type { FsListItem } from "@/lib/api";

export function previewIsAffected(file: FsListItem, activePath: string | null) {
  if (!activePath) {
    return false;
  }
  if (file.type === "file") {
    return normalizeWorkspacePath(activePath) === normalizeWorkspacePath(file.path);
  }
  const parent = normalizeWorkspacePath(file.path);
  const child = normalizeWorkspacePath(activePath);
  return child === parent || child.startsWith(`${parent}/`);
}

function normalizeWorkspacePath(path: string) {
  const trimmed = path.trim();
  if (!trimmed || trimmed === "/") {
    return "/";
  }
  return `/${trimmed.replace(/^\/+/, "").replace(/\/+$/, "")}`;
}

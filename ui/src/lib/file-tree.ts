import type { FsListItem } from "@/lib/api";

export const TREE_MIN_HEIGHT = 220;
export const TREE_HEIGHT_OFFSET = 310;

export type FileAction = "delete" | "move";

export type FileTreeNode = FsListItem & {
  id: string;
  children?: FileTreeNode[];
  error?: string | null;
  loaded?: boolean;
  loading?: boolean;
};

export type SortKey = "name" | "modified" | "size" | "type";
export type SortDirection = "asc" | "desc";

export function sortFiles(
  files: FileTreeNode[],
  sortKey: SortKey,
  sortDirection: SortDirection,
  directoriesFirst: boolean,
): FileTreeNode[];
export function sortFiles(
  files: FsListItem[],
  sortKey: SortKey,
  sortDirection: SortDirection,
  directoriesFirst: boolean,
): FsListItem[];
export function sortFiles<T extends FsListItem>(
  files: T[],
  sortKey: SortKey,
  sortDirection: SortDirection,
  directoriesFirst: boolean,
): T[] {
  const direction = sortDirection === "asc" ? 1 : -1;
  return [...files].sort((left, right) => {
    if (directoriesFirst && left.type !== right.type) {
      return left.type === "directory" ? -1 : 1;
    }
    return compareFiles(left, right, sortKey) * direction;
  });
}

export function sortTree(
  nodes: FileTreeNode[],
  sortKey: SortKey,
  sortDirection: SortDirection,
): FileTreeNode[] {
  return sortFiles(nodes, sortKey, sortDirection, true).map((node) => ({
    ...node,
    children: node.children
      ? sortTree(node.children, sortKey, sortDirection)
      : node.children,
  }));
}

export function toTreeNode(file: FsListItem): FileTreeNode {
  return {
    ...file,
    id: file.path,
    children: file.type === "directory" ? [] : undefined,
    loaded: file.type === "file",
    loading: false,
    error: null,
  };
}

export function joinWorkspacePath(parentPath: string, name: string) {
  const parent = normalizePath(parentPath);
  if (parent === "/") {
    return `/${name}`;
  }
  return `${parent}/${name}`;
}

export function normalizePath(path: string) {
  const trimmed = path.trim();
  if (!trimmed || trimmed === "/") {
    return "/";
  }
  return `/${trimmed.replace(/^\/+/, "").replace(/\/+$/, "")}`;
}

export function currentTreeHeight(viewportHeight: number | null) {
  if (viewportHeight === null) {
    return TREE_MIN_HEIGHT;
  }
  return Math.max(TREE_MIN_HEIGHT, viewportHeight - TREE_HEIGHT_OFFSET);
}

function compareFiles(left: FsListItem, right: FsListItem, sortKey: SortKey) {
  if (sortKey === "modified") {
    return (left.modified_at ?? 0) - (right.modified_at ?? 0);
  }
  if (sortKey === "size") {
    return (left.size ?? -1) - (right.size ?? -1);
  }
  if (sortKey === "type") {
    return textCompare(left.type, right.type) || textCompare(left.name, right.name);
  }
  return textCompare(left.name, right.name);
}

function textCompare(left: string, right: string) {
  return left.localeCompare(right, undefined, { sensitivity: "base" });
}

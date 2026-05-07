import { useCallback, useEffect, useRef, useState } from "react";

import type { FsListItem } from "@/lib/api";
import { listFiles } from "@/lib/api";
import type { FileTreeNode } from "@/lib/file-tree";
import { toTreeNode } from "@/lib/file-tree";

export function useFileTree({
  rootFiles,
  resetKey,
  sessionUuid,
  userId,
}: {
  rootFiles: FsListItem[];
  resetKey: number;
  sessionUuid: string;
  userId: string;
}) {
  const [nodes, setNodes] = useState<FileTreeNode[]>(() =>
    rootFiles.map((file) => toTreeNode(file)),
  );
  const loadedPathsRef = useRef<Set<string>>(new Set(["/"]));
  const loadingPathsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    loadedPathsRef.current = new Set(["/"]);
    loadingPathsRef.current = new Set();
    setNodes(rootFiles.map((file) => toTreeNode(file)));
  }, [resetKey, rootFiles]);

  const loadChildren = useCallback(
    async (path: string) => {
      if (
        loadedPathsRef.current.has(path) ||
        loadingPathsRef.current.has(path)
      ) {
        return;
      }

      loadingPathsRef.current.add(path);
      setNodes((current) =>
        updateNode(current, path, (node) => ({
          ...node,
          error: null,
          loading: true,
        })),
      );

      try {
        const result = await listFiles({ userId, sessionUuid, path });
        loadedPathsRef.current.add(path);
        setNodes((current) =>
          updateNode(current, path, (node) => ({
            ...node,
            children: result.files.map((file) => toTreeNode(file)),
            error: null,
            loaded: true,
            loading: false,
          })),
        );
      } catch (error) {
        setNodes((current) =>
          updateNode(current, path, (node) => ({
            ...node,
            error: error instanceof Error ? error.message : "Folder load failed.",
            loading: false,
          })),
        );
      } finally {
        loadingPathsRef.current.delete(path);
      }
    },
    [sessionUuid, userId],
  );

  return {
    loadChildren,
    nodes,
  };
}

function updateNode(
  nodes: FileTreeNode[],
  path: string,
  update: (node: FileTreeNode) => FileTreeNode,
): FileTreeNode[] {
  return nodes.map((node) => {
    if (node.path === path) {
      return update(node);
    }
    if (!node.children) {
      return node;
    }
    return {
      ...node,
      children: updateNode(node.children, path, update),
    };
  });
}

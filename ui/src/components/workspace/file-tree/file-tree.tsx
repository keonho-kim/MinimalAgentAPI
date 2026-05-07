import { useCallback, useMemo, useState } from "react";
import { Tree } from "react-arborist";
import type { MoveHandler, NodeApi, RenameHandler } from "react-arborist";

import { FileActionDialog } from "@/components/workspace/file-tree/file-action-dialog";
import { FileTreeRow } from "@/components/workspace/file-tree/file-tree-row";
import { useFileTree } from "@/hooks/use-file-tree";
import { useFileTreeHeight } from "@/hooks/use-file-tree-height";
import type { FsListItem } from "@/lib/api";
import type { FileAction, FileTreeNode, SortDirection, SortKey } from "@/lib/file-tree";
import { joinWorkspacePath, normalizePath, sortFiles, sortTree, toTreeNode } from "@/lib/file-tree";

const TREE_ROW_HEIGHT = 32;
const TREE_INDENT = 18;

export function FileTree({
  files,
  isPreviewSupported,
  mode,
  operationPendingPath,
  resetKey,
  searchFiles,
  sessionUuid,
  sortDirection,
  sortKey,
  userId,
  onDelete,
  onMove,
  onPreview,
  onRename,
  onTreeReload,
}: {
  files: FsListItem[];
  isPreviewSupported(filename: string): boolean;
  mode: "tree" | "search";
  operationPendingPath: string | null;
  resetKey: number;
  searchFiles: FsListItem[];
  sessionUuid: string;
  sortDirection: SortDirection;
  sortKey: SortKey;
  userId: string;
  onDelete(file: FsListItem): Promise<void>;
  onMove(file: FsListItem, destinationPath: string): Promise<void>;
  onPreview(file: FsListItem): void;
  onRename(file: FsListItem, name: string): Promise<void>;
  onTreeReload(): void;
}) {
  const [actionCandidate, setActionCandidate] = useState<FileTreeNode | null>(null);
  const [actionType, setActionType] = useState<FileAction | null>(null);
  const [movePath, setMovePath] = useState("");
  const treeHeight = useFileTreeHeight();
  const tree = useFileTree({ rootFiles: files, resetKey, sessionUuid, userId });
  const data = useMemo(
    () =>
      mode === "search"
        ? sortFiles(searchFiles, sortKey, sortDirection, false).map(toTreeNode)
        : sortTree(tree.nodes, sortKey, sortDirection),
    [mode, searchFiles, sortDirection, sortKey, tree.nodes],
  );

  const openNode = useCallback(
    (node: NodeApi<FileTreeNode>) => {
      if (node.data.type === "directory") {
        node.toggle();
        return;
      }
      if (isPreviewSupported(node.data.name)) {
        onPreview(node.data);
      }
    },
    [isPreviewSupported, onPreview],
  );

  const beginAction = useCallback((type: FileAction, file: FileTreeNode) => {
    setActionCandidate(file);
    setActionType(type);
    setMovePath(file.path);
  }, []);

  const resetAction = useCallback(() => {
    setActionCandidate(null);
    setActionType(null);
    setMovePath("");
  }, []);

  const confirmAction = useCallback(async () => {
    if (!actionCandidate || !actionType) {
      return;
    }

    try {
      if (actionType === "delete") {
        await onDelete(actionCandidate);
        resetAction();
        onTreeReload();
        return;
      }

      await onMove(actionCandidate, movePath.trim());
      resetAction();
      onTreeReload();
    } catch {
      onTreeReload();
    }
  }, [actionCandidate, actionType, movePath, onDelete, onMove, onTreeReload, resetAction]);

  const renameNode = useCallback(
    async ({ name, node }) => {
      try {
        await onRename(node.data, name);
      } finally {
        onTreeReload();
      }
    },
    [onRename, onTreeReload],
  ) satisfies RenameHandler<FileTreeNode>;

  const moveNodes = useCallback(
    async ({ dragNodes, parentNode }) => {
      try {
        for (const node of dragNodes) {
          const destinationPath = joinWorkspacePath(parentNode?.data.path ?? "/", node.data.name);
          if (normalizePath(destinationPath) === normalizePath(node.data.path)) {
            continue;
          }
          await onMove(node.data, destinationPath);
        }
      } catch {
        // The drawer status exposes the mutation error.
      } finally {
        onTreeReload();
      }
    },
    [onMove, onTreeReload],
  ) satisfies MoveHandler<FileTreeNode>;

  return (
    <div className="min-h-0">
      {data.length === 0 ? (
        <div className="rounded-lg border border-dashed bg-background p-4 text-sm text-muted-foreground">
          {mode === "search" ? "검색 결과가 없습니다." : "표시할 파일이 없습니다."}
        </div>
      ) : (
        <Tree<FileTreeNode>
          data={data}
          disableMultiSelection
          disableDrop={({ dragNodes, parentNode }) => {
            if (mode === "search") {
              return true;
            }
            if (parentNode && parentNode.data.type !== "directory") {
              return true;
            }
            return dragNodes.some((node) => (
              parentNode !== null &&
              node.data.type === "directory" &&
              node.isAncestorOf(parentNode)
            ));
          }}
          height={treeHeight}
          idAccessor="id"
          indent={TREE_INDENT}
          openByDefault={false}
          overscanCount={4}
          rowHeight={TREE_ROW_HEIGHT}
          width="100%"
          onMove={moveNodes}
          onRename={renameNode}
          onToggle={(path) => {
            if (mode === "tree") {
              void tree.loadChildren(path);
            }
          }}
        >
          {(props) => (
            <FileTreeRow
              {...props}
              isPreviewSupported={isPreviewSupported}
              operationPendingPath={operationPendingPath}
              showPath={mode === "search"}
              onBeginAction={beginAction}
              onOpen={openNode}
            />
          )}
        </Tree>
      )}
      <FileActionDialog
        actionCandidate={actionCandidate}
        actionType={actionType}
        movePath={movePath}
        operationPendingPath={operationPendingPath}
        onConfirm={() => void confirmAction()}
        onMovePathChange={setMovePath}
        onReset={resetAction}
      />
    </div>
  );
}

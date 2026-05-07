import { ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import type { NodeApi, NodeRendererProps } from "react-arborist";

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { Input } from "@/components/ui/input";
import { writeFileMentionDragPayload } from "@/lib/file-mentions";
import { FileTreeIcon } from "@/lib/file-icons";
import type { FileAction, FileTreeNode } from "@/lib/file-tree";
import { cn } from "@/lib/utils";

export function FileTreeRow({
  dragHandle,
  isPreviewSupported,
  node,
  operationPendingPath,
  showPath,
  style,
  onBeginAction,
  onOpen,
}: NodeRendererProps<FileTreeNode> & {
  isPreviewSupported(filename: string): boolean;
  operationPendingPath: string | null;
  showPath: boolean;
  onBeginAction(type: FileAction, file: FileTreeNode): void;
  onOpen(node: NodeApi<FileTreeNode>): void;
}) {
  const [editValue, setEditValue] = useState(node.data.name);
  const cancelEditRef = useRef(false);
  const isDirectory = node.data.type === "directory";
  const isPending = operationPendingPath === node.data.path;
  const canPreview = node.data.type === "file" && isPreviewSupported(node.data.name);
  const canAttachByDrag = node.data.type === "file" && !isPending;

  useEffect(() => {
    if (node.isEditing) {
      setEditValue(node.data.name);
      cancelEditRef.current = false;
    }
  }, [node.data.name, node.isEditing]);

  const handleNativeDragStart = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      if (node.data.type !== "file" || isPending) {
        return;
      }
      writeFileMentionDragPayload(
        event.dataTransfer,
        {
          name: node.data.name,
          path: node.data.path,
        },
        { effectAllowed: "copyMove" },
      );
    },
    [isPending, node.data.name, node.data.path, node.data.type],
  );

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <div
          className={cn(
            "group flex h-full min-w-0 items-center gap-2 rounded-md pr-2 text-sm text-foreground hover:bg-secondary",
            node.isSelected && "bg-secondary",
            isPending && "opacity-50",
            canAttachByDrag && "cursor-grab select-none active:cursor-grabbing",
          )}
          draggable={canAttachByDrag ? true : undefined}
          ref={dragHandle}
          style={style}
          onClick={() => {
            if (!node.isEditing) {
              node.select();
            }
          }}
          onDoubleClick={() => onOpen(node)}
          onDragStart={handleNativeDragStart}
          onDragStartCapture={handleNativeDragStart}
        >
          {isDirectory ? (
            <button
              className="flex size-5 shrink-0 items-center justify-center rounded-sm text-muted-foreground hover:bg-background hover:text-foreground"
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                node.toggle();
              }}
            >
              <ChevronRight
                className={cn("size-4 transition-transform", node.isOpen && "rotate-90")}
              />
              <span className="sr-only">{node.isOpen ? "접기" : "펼치기"}</span>
            </button>
          ) : (
            <span className="size-5 shrink-0" aria-hidden />
          )}
          <FileTreeIcon
            className="size-[1.4rem] shrink-0 text-muted-foreground"
            isOpen={node.isOpen}
            name={node.data.name}
            type={node.data.type}
          />
          {node.isEditing ? (
            <form
              className="min-w-0 flex-1"
              onClick={(event) => event.stopPropagation()}
              onSubmit={(event) => {
                event.preventDefault();
                node.submit(editValue.trim());
              }}
            >
              <Input
                autoFocus
                className="h-7"
                value={editValue}
                onBlur={() => {
                  if (cancelEditRef.current) {
                    node.reset();
                    return;
                  }
                  node.submit(editValue.trim());
                }}
                onChange={(event) => setEditValue(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    cancelEditRef.current = true;
                    node.reset();
                  }
                }}
              />
            </form>
          ) : (
            <div className="min-w-0 flex-1 text-left">
              <span className="block min-w-0 break-words leading-5">
                {node.data.name}
              </span>
              {showPath ? (
                <span className="block min-w-0 break-words text-xs text-muted-foreground">
                  {node.data.path}
                </span>
              ) : null}
              {node.data.loading ? (
                <span className="block text-xs text-muted-foreground">불러오는 중</span>
              ) : null}
              {node.data.error ? (
                <span className="block break-words text-xs text-destructive">
                  {node.data.error}
                </span>
              ) : null}
            </div>
          )}
        </div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem
          disabled={!isDirectory && !canPreview}
          onSelect={() => onOpen(node)}
        >
          열기
        </ContextMenuItem>
        <ContextMenuItem onSelect={() => void node.edit()}>
          이름 바꾸기
        </ContextMenuItem>
        <ContextMenuItem onSelect={() => onBeginAction("move", node.data)}>
          이동하기
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem
          variant="destructive"
          onSelect={() => onBeginAction("delete", node.data)}
        >
          삭제하기
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

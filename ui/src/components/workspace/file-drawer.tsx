import { PanelRightClose } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  CSSProperties,
  KeyboardEvent,
  PointerEvent,
} from "react";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  FileTree,
  sortFiles,
} from "@/components/workspace/file-tree";
import type { SortDirection, SortKey } from "@/components/workspace/file-tree";
import type { FsListItem } from "@/lib/api";
import { searchFiles } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { FileDrawerToolbar } from "./file-drawer-toolbar";
import { FileDrawerUpload } from "./file-drawer-upload";
import {
  DRAWER_KEYBOARD_STEP,
  MAX_DRAWER_WIDTH,
  MIN_DRAWER_WIDTH,
  SEARCH_LIMIT,
  clampDrawerWidth,
  drawerStatus,
  maxViewportWidth,
} from "./file-drawer-utils";

export function FileDrawer({
  open,
  drawerWidth,
  files,
  operationPendingPath,
  status,
  onDelete,
  onDrawerWidthChange,
  onMove,
  onOpenChange,
  onRefresh,
  onRename,
  onUploadFiles,
  onPreview,
  isPreviewSupported,
  focusPath,
  sessionUuid,
  userId,
}: {
  open: boolean;
  drawerWidth: number;
  files: FsListItem[];
  operationPendingPath: string | null;
  status: string;
  onDelete(file: FsListItem): Promise<void>;
  onDrawerWidthChange(width: number): void;
  onMove(file: FsListItem, destinationPath: string): Promise<void>;
  onOpenChange(open: boolean): void;
  onRefresh(): void;
  onRename(file: FsListItem, name: string): Promise<void>;
  onUploadFiles(files: File[]): Promise<void>;
  onPreview(file: FsListItem): void;
  isPreviewSupported(filename: string): boolean;
  focusPath: string | null;
  sessionUuid: string;
  userId: string;
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [treeResetKey, setTreeResetKey] = useState(0);
  const cleanSearchQuery = searchQuery.trim();
  const searchQueryResult = useQuery({
    queryKey: queryKeys.fileSearch(userId, sessionUuid, cleanSearchQuery, SEARCH_LIMIT),
    queryFn: () =>
      searchFiles({
        userId,
        sessionUuid,
        query: cleanSearchQuery,
        limit: SEARCH_LIMIT,
      }),
    enabled: open && cleanSearchQuery.length > 0,
  });
  const searchMatches = useMemo(
    () =>
      sortFiles(
        searchQueryResult.data?.matches ?? [],
        sortKey,
        sortDirection,
        false,
      ),
    [searchQueryResult.data?.matches, sortDirection, sortKey],
  );
  const clampedWidth = clampDrawerWidth(drawerWidth);
  const drawerStyle = {
    "--file-drawer-width": `${clampedWidth}px`,
  } as CSSProperties;
  const statusMessage = drawerStatus(status, cleanSearchQuery, searchQueryResult);

  useEffect(() => {
    if (!open || !focusPath) {
      return;
    }
    setSearchQuery(fileSearchQuery(focusPath));
    setTreeResetKey((current) => current + 1);
  }, [focusPath, open]);

  const reloadTree = useCallback(() => {
    setTreeResetKey((current) => current + 1);
  }, []);

  const beginResize = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      const startX = event.clientX;
      const startWidth = clampedWidth;

      const handlePointerMove = (moveEvent: globalThis.PointerEvent) => {
        onDrawerWidthChange(
          clampDrawerWidth(startWidth + startX - moveEvent.clientX),
        );
      };
      const stopResize = () => {
        window.removeEventListener("pointermove", handlePointerMove);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };

      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      window.addEventListener("pointermove", handlePointerMove);
      window.addEventListener("pointerup", stopResize, { once: true });
    },
    [clampedWidth, onDrawerWidthChange],
  );

  const handleResizeKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        onDrawerWidthChange(clampDrawerWidth(clampedWidth + DRAWER_KEYBOARD_STEP));
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        onDrawerWidthChange(clampDrawerWidth(clampedWidth - DRAWER_KEYBOARD_STEP));
        return;
      }
      if (event.key === "Home") {
        event.preventDefault();
        onDrawerWidthChange(MIN_DRAWER_WIDTH);
        return;
      }
      if (event.key === "End") {
        event.preventDefault();
        onDrawerWidthChange(clampDrawerWidth(MAX_DRAWER_WIDTH));
      }
    },
    [clampedWidth, onDrawerWidthChange],
  );

  const toggleSortDirection = useCallback(() => {
    setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
  }, []);

  const uploadFileList = useCallback(
    async (fileList: File[]) => {
      try {
        await onUploadFiles(fileList);
        reloadTree();
      } catch {
        // The drawer status exposes the mutation error.
      }
    },
    [onUploadFiles, reloadTree],
  );

  const refresh = useCallback(() => {
    onRefresh();
    reloadTree();
  }, [onRefresh, reloadTree]);

  return (
    <Sheet modal={false} open={open} onOpenChange={onOpenChange}>
      <SheetContent
        className="w-[calc(100vw-1rem)] max-w-none p-0 sm:w-[var(--file-drawer-width)]"
        showClose={false}
        showOverlay={false}
        style={drawerStyle}
      >
        <div
          aria-label="파일 드로어 너비 조절"
          aria-orientation="vertical"
          aria-valuemax={Math.min(MAX_DRAWER_WIDTH, maxViewportWidth())}
          aria-valuemin={MIN_DRAWER_WIDTH}
          aria-valuenow={clampedWidth}
          className="absolute inset-y-0 left-0 hidden w-2 cursor-col-resize touch-none items-stretch justify-center sm:flex"
          role="separator"
          tabIndex={0}
          onKeyDown={handleResizeKeyDown}
          onPointerDown={beginResize}
        >
          <span className="my-auto h-12 w-px rounded-full bg-border transition-colors" />
        </div>
        <div className="flex h-full min-h-0 flex-col p-5">
          <Button
            className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
            size="icon"
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
          >
            <PanelRightClose />
            <span className="sr-only">파일 드로어 접기</span>
          </Button>
          <SheetHeader className="pr-10">
            <SheetTitle>작업공간 파일</SheetTitle>
            {statusMessage ? (
              <SheetDescription>{statusMessage}</SheetDescription>
            ) : null}
          </SheetHeader>
          <FileDrawerUpload onUploadFiles={uploadFileList} />
          <FileDrawerToolbar
            searchQuery={searchQuery}
            sortDirection={sortDirection}
            sortKey={sortKey}
            onRefresh={refresh}
            onSearchQueryChange={setSearchQuery}
            onSortDirectionToggle={toggleSortDirection}
            onSortKeyChange={setSortKey}
          />
          <div className="mt-5 min-h-0 flex-1">
            <FileTree
              files={files}
              isPreviewSupported={isPreviewSupported}
              mode={cleanSearchQuery ? "search" : "tree"}
              operationPendingPath={operationPendingPath}
              resetKey={treeResetKey}
              searchFiles={searchMatches}
              sessionUuid={sessionUuid}
              sortDirection={sortDirection}
              sortKey={sortKey}
              userId={userId}
              onDelete={onDelete}
              onMove={onMove}
              onPreview={onPreview}
              onRename={onRename}
              onTreeReload={reloadTree}
            />
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function fileSearchQuery(path: string) {
  return path.split("/").filter(Boolean).at(-1) ?? path;
}

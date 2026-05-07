import { ArrowDownAZ, ArrowUpAZ, PanelRightClose, RefreshCw, Upload } from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import type {
  CSSProperties,
  ChangeEvent,
  DragEvent,
  KeyboardEvent,
  PointerEvent,
} from "react";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { cn } from "@/lib/utils";

const MIN_DRAWER_WIDTH = 320;
const DEFAULT_DRAWER_WIDTH = 760;
const MAX_DRAWER_WIDTH = 950;
const VIEWPORT_PADDING = 64;
const DRAWER_KEYBOARD_STEP = 24;
const SEARCH_LIMIT = 50;

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
  sessionUuid: string;
  userId: string;
}) {
  const [dragActive, setDragActive] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [treeResetKey, setTreeResetKey] = useState(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
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

  const uploadFileList = useCallback(
    async (fileList: File[]) => {
      if (!fileList.length) {
        return;
      }
      try {
        await onUploadFiles(fileList);
        reloadTree();
      } catch {
        // The drawer status exposes the mutation error.
      }
    },
    [onUploadFiles, reloadTree],
  );

  const handleFileInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const nextFiles = Array.from(event.target.files ?? []);
      event.target.value = "";
      void uploadFileList(nextFiles);
    },
    [uploadFileList],
  );

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    if (!hasDraggedFiles(event)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.stopPropagation();
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      if (!hasDraggedFiles(event)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      setDragActive(false);
      void uploadFileList(Array.from(event.dataTransfer.files));
    },
    [uploadFileList],
  );

  const toggleSortDirection = useCallback(() => {
    setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
  }, []);

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
          <input
            className="hidden"
            multiple
            ref={fileInputRef}
            type="file"
            onChange={handleFileInputChange}
          />
          <div
            className={cn(
              "mt-5 rounded-lg border border-dashed bg-background p-3 transition-colors",
              dragActive && "border-ring bg-accent/40",
            )}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <Button
              className="mx-auto flex w-full max-w-[16rem]"
              type="button"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload data-icon="inline-start" />
              업로드
            </Button>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              여기에 파일을 놓으면 업로드됩니다.
            </p>
          </div>
          <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] gap-2">
            <Input
              placeholder="파일 검색"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
            <Button variant="outline" onClick={refresh}>
              <RefreshCw data-icon="inline-start" />
              새로고침
            </Button>
          </div>
          <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] gap-2">
            <select
              className="h-9 min-w-0 rounded-md border bg-card px-3 text-sm text-foreground shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              value={sortKey}
              onChange={(event) => setSortKey(event.target.value as SortKey)}
            >
              <option value="name">이름</option>
              <option value="modified">수정일</option>
              <option value="size">크기</option>
              <option value="type">유형</option>
            </select>
            <Button
              size="icon"
              type="button"
              variant="outline"
              onClick={toggleSortDirection}
            >
              {sortDirection === "asc" ? (
                <ArrowDownAZ data-icon="inline-start" />
              ) : (
                <ArrowUpAZ data-icon="inline-start" />
              )}
              <span className="sr-only">정렬 방향 전환</span>
            </Button>
          </div>
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

function clampDrawerWidth(width: number) {
  return Math.min(maxViewportWidth(), Math.max(MIN_DRAWER_WIDTH, Math.round(width)));
}

function maxViewportWidth() {
  if (typeof window === "undefined") {
    return DEFAULT_DRAWER_WIDTH;
  }
  return Math.max(
    MIN_DRAWER_WIDTH,
    Math.min(MAX_DRAWER_WIDTH, window.innerWidth - VIEWPORT_PADDING),
  );
}

function hasDraggedFiles(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.types).includes("Files");
}

function drawerStatus(
  status: string,
  searchQuery: string,
  searchQueryResult: {
    error: unknown;
    isFetching: boolean;
  },
) {
  if (searchQuery && searchQueryResult.isFetching) {
    return "검색 중";
  }
  if (searchQuery && searchQueryResult.error) {
    return "파일 시스템에 연결할 수 없습니다. 백엔드를 확인한 뒤 새로고침해 주세요.";
  }
  if (isFailureStatus(status)) {
    return "파일 시스템에 연결할 수 없습니다. 백엔드를 확인한 뒤 새로고침해 주세요.";
  }
  if (status === "Ready") {
    return "";
  }
  if (status === "Loading") {
    return "불러오는 중";
  }
  if (status === "Uploading") {
    return "업로드 중";
  }
  if (status === "Deleting") {
    return "삭제 중";
  }
  if (status === "Moving") {
    return "이동 중";
  }
  if (status === "Renaming") {
    return "이름 변경 중";
  }
  return status;
}

function isFailureStatus(status: string) {
  return /failed|error|cannot|unable/i.test(status);
}

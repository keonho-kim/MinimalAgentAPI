import { ArrowDownAZ, ArrowUpAZ, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SortDirection, SortKey } from "@/components/workspace/file-tree";

export function FileDrawerToolbar({
  searchQuery,
  sortDirection,
  sortKey,
  onRefresh,
  onSearchQueryChange,
  onSortDirectionToggle,
  onSortKeyChange,
}: {
  searchQuery: string;
  sortDirection: SortDirection;
  sortKey: SortKey;
  onRefresh(): void;
  onSearchQueryChange(query: string): void;
  onSortDirectionToggle(): void;
  onSortKeyChange(sortKey: SortKey): void;
}) {
  return (
    <>
      <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] gap-2">
        <Input
          placeholder="파일 검색"
          value={searchQuery}
          onChange={(event) => onSearchQueryChange(event.target.value)}
        />
        <Button variant="outline" onClick={onRefresh}>
          <RefreshCw data-icon="inline-start" />
          새로고침
        </Button>
      </div>
      <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] gap-2">
        <select
          className="h-9 min-w-0 rounded-md border bg-card px-3 text-sm text-foreground shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          value={sortKey}
          onChange={(event) => onSortKeyChange(event.target.value as SortKey)}
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
          onClick={onSortDirectionToggle}
        >
          {sortDirection === "asc" ? (
            <ArrowDownAZ data-icon="inline-start" />
          ) : (
            <ArrowUpAZ data-icon="inline-start" />
          )}
          <span className="sr-only">정렬 방향 전환</span>
        </Button>
      </div>
    </>
  );
}

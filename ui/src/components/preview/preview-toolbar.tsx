import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react";
import { memo } from "react";

import { Button } from "@/components/ui/button";

export const PreviewToolbar = memo(function PreviewToolbar({
  page,
  pageCount,
  scale,
  canGoPrev,
  canGoNext,
  onPrev,
  onNext,
  onZoomOut,
  onZoomIn,
}: {
  page: number;
  pageCount: number;
  scale: number;
  canGoPrev: boolean;
  canGoNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  onZoomOut: () => void;
  onZoomIn: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b bg-card px-5 py-3">
      <div className="flex items-center gap-1">
        <Button disabled={!canGoPrev} size="icon" variant="outline" onClick={onPrev}>
          <ChevronLeft data-icon="inline-start" />
          <span className="sr-only">Previous page</span>
        </Button>
        <Button disabled={!canGoNext} size="icon" variant="outline" onClick={onNext}>
          <ChevronRight data-icon="inline-start" />
          <span className="sr-only">Next page</span>
        </Button>
        <span className="px-2 text-sm text-muted-foreground">
          {pageCount ? `${page} / ${pageCount}` : "Loading"}
        </span>
      </div>
      <div className="flex items-center gap-1">
        <Button size="icon" variant="outline" onClick={onZoomOut}>
          <ZoomOut data-icon="inline-start" />
          <span className="sr-only">Zoom out</span>
        </Button>
        <span className="w-14 text-center text-sm text-muted-foreground">
          {Math.round(scale * 100)}%
        </span>
        <Button size="icon" variant="outline" onClick={onZoomIn}>
          <ZoomIn data-icon="inline-start" />
          <span className="sr-only">Zoom in</span>
        </Button>
      </div>
    </div>
  );
});

import {
  ChevronLeft,
  ChevronRight,
  Redo2,
  Save,
  Undo2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import type { PptxElement, PptxSlide } from "@/lib/api";
import type { PptxTextShapeDraft } from "./types";

export function PptxEditorToolbar({
  draft,
  redoDisabled,
  savePending,
  scale,
  selectedElement,
  selectedSlide,
  slides,
  undoDisabled,
  onNextSlide,
  onPreviousSlide,
  onRedo,
  onSave,
  onScaleChange,
  onUndo,
}: {
  draft: PptxTextShapeDraft | null;
  redoDisabled: boolean;
  savePending: boolean;
  scale: number;
  selectedElement: PptxElement | null;
  selectedSlide: PptxSlide | null;
  slides: PptxSlide[];
  undoDisabled: boolean;
  onNextSlide(): void;
  onPreviousSlide(): void;
  onRedo(): void;
  onSave(): void;
  onScaleChange(scale: number): void;
  onUndo(): void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b bg-card px-4 py-2.5">
      <div className="flex items-center gap-1">
        <Button
          disabled={!selectedSlide || selectedSlide.index <= 1}
          size="icon"
          type="button"
          variant="outline"
          onClick={onPreviousSlide}
        >
          <ChevronLeft data-icon="inline-start" />
          <span className="sr-only">Previous slide</span>
        </Button>
        <Button
          disabled={!selectedSlide || selectedSlide.index >= slides.length}
          size="icon"
          type="button"
          variant="outline"
          onClick={onNextSlide}
        >
          <ChevronRight data-icon="inline-start" />
          <span className="sr-only">Next slide</span>
        </Button>
        <span className="px-2 text-sm text-muted-foreground">
          {selectedSlide ? `${selectedSlide.index} / ${slides.length}` : "Loading"}
        </span>
      </div>
      <div className="flex items-center gap-1">
        <Button disabled={undoDisabled} size="icon" type="button" variant="outline" onClick={onUndo}>
          <Undo2 data-icon="inline-start" />
          <span className="sr-only">Undo</span>
        </Button>
        <Button disabled={redoDisabled} size="icon" type="button" variant="outline" onClick={onRedo}>
          <Redo2 data-icon="inline-start" />
          <span className="sr-only">Redo</span>
        </Button>
        <Button
          size="sm"
          type="button"
          variant="outline"
          onClick={() => onScaleChange(Math.max(scale - 0.2, 0.5))}
        >
          <ZoomOut data-icon="inline-start" />
          축소
        </Button>
        <span className="w-14 text-center text-sm text-muted-foreground">
          {Math.round(scale * 100)}%
        </span>
        <Button
          size="sm"
          type="button"
          variant="outline"
          onClick={() => onScaleChange(Math.min(scale + 0.2, 2.5))}
        >
          <ZoomIn data-icon="inline-start" />
          확대
        </Button>
        <Button
          disabled={!selectedElement || !draft || savePending}
          size="sm"
          type="button"
          onClick={onSave}
        >
          <Save data-icon="inline-start" />
          저장
        </Button>
      </div>
    </div>
  );
}

import { useEffect, useRef } from "react";

import type { PptxSlide } from "@/lib/api";
import { cn } from "@/lib/utils";

import type { PdfDocument } from "./types";

export function PptxSlidePanel({
  document,
  selectedSlideId,
  slides,
  onSelectSlide,
}: {
  document: PdfDocument | null;
  selectedSlideId: string | null;
  slides: PptxSlide[];
  onSelectSlide: (slideId: string) => void;
}) {
  return (
    <aside className="min-h-0 border-r bg-card">
      <div className="border-b px-3 py-3">
        <h3 className="text-sm font-medium">Slides</h3>
        <p className="mt-1 text-xs text-muted-foreground">{slides.length} slides</p>
      </div>
      <div className="h-[calc(100%-4.25rem)] overflow-y-auto p-2">
        <div className="flex flex-col gap-2">
          {slides.map((slide) => (
            <button
              aria-current={slide.id === selectedSlideId ? "page" : undefined}
              className={cn(
                "group rounded-md border bg-background p-1.5 text-left transition-colors hover:border-foreground/30",
                slide.id === selectedSlideId && "border-foreground bg-secondary",
              )}
              key={slide.id}
              type="button"
              onClick={() => onSelectSlide(slide.id)}
            >
              <SlideThumbnail
                document={document}
                selected={slide.id === selectedSlideId}
                slideNumber={slide.index}
              />
              <div className="mt-1 truncate text-center text-[11px] font-medium text-muted-foreground">
                {slide.index}
              </div>
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}

function SlideThumbnail({
  document,
  selected,
  slideNumber,
}: {
  document: PdfDocument | null;
  selected: boolean;
  slideNumber: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function renderThumbnail() {
      if (!document || !canvasRef.current) {
        return;
      }
      const page = await document.getPage(slideNumber);
      if (cancelled || !canvasRef.current) {
        return;
      }
      const viewport = page.getViewport({ scale: 0.16 });
      const canvas = canvasRef.current;
      const context = canvas.getContext("2d");
      if (!context) {
        return;
      }
      canvas.width = Math.ceil(viewport.width);
      canvas.height = Math.ceil(viewport.height);
      await page.render({ canvas, canvasContext: context, viewport }).promise;
    }

    void renderThumbnail();
    return () => {
      cancelled = true;
    };
  }, [document, slideNumber]);

  return (
    <div
      className={cn(
        "grid aspect-[4/3] place-items-center overflow-hidden rounded-sm border bg-muted",
        selected && "border-foreground",
      )}
    >
      <canvas className="max-h-full max-w-full" ref={canvasRef} />
    </div>
  );
}

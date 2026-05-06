import DOMPurify from "dompurify";
import { memo, useEffect, useState } from "react";

import { PreviewToolbar } from "@/components/preview/preview-toolbar";
import { ScrollArea } from "@/components/ui/scroll-area";

type RhwpDocument = {
  pageCount: () => number;
  renderPageSvg: (pageIndex: number) => string;
};

type MeasureGlobal = typeof globalThis & {
  measureTextWidth?: (font: string, text: string) => number;
};

export const HwpxViewer = memo(function HwpxViewer({
  sourceUrl,
}: {
  sourceUrl: string;
}) {
  const [document, setDocument] = useState<RhwpDocument | null>(null);
  const [page, setPage] = useState(1);
  const [scale, setScale] = useState(1);
  const [svg, setSvg] = useState("");
  const [status, setStatus] = useState("Loading HWPX");

  useEffect(() => {
    let cancelled = false;

    async function loadHwpx() {
      setStatus("Loading HWPX");
      setDocument(null);
      setPage(1);
      ensureMeasureTextWidth();
      const [rhwp, response] = await Promise.all([
        import("@rhwp/core"),
        fetch(sourceUrl),
      ]);
      if (!response.ok) {
        throw new Error(`HWPX source failed: ${response.status}`);
      }
      await rhwp.default();
      const buffer = new Uint8Array(await response.arrayBuffer());
      const nextDocument = new rhwp.HwpDocument(buffer) as RhwpDocument;
      if (cancelled) {
        return;
      }
      setDocument(nextDocument);
      setStatus("Ready");
    }

    loadHwpx().catch((error: unknown) => {
      setStatus(error instanceof Error ? error.message : "HWPX preview failed.");
    });

    return () => {
      cancelled = true;
    };
  }, [sourceUrl]);

  useEffect(() => {
    if (!document) {
      setSvg("");
      return;
    }
    try {
      setSvg(DOMPurify.sanitize(document.renderPageSvg(page - 1)));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "HWPX render failed.");
    }
  }, [document, page]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PreviewToolbar
        canGoNext={Boolean(document && page < document.pageCount())}
        canGoPrev={page > 1}
        page={page}
        pageCount={document?.pageCount() ?? 0}
        scale={scale}
        onNext={() =>
          setPage((current) => Math.min(current + 1, document?.pageCount() ?? current))
        }
        onPrev={() => setPage((current) => Math.max(current - 1, 1))}
        onZoomIn={() => setScale((current) => Math.min(current + 0.25, 3))}
        onZoomOut={() => setScale((current) => Math.max(current - 0.25, 0.5))}
      />
      <ScrollArea className="min-h-0 flex-1">
        <div className="flex min-h-full justify-center p-5">
          <div
            className="h-fit origin-top border bg-card"
            style={{ transform: `scale(${scale})` }}
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        </div>
      </ScrollArea>
      <div className="border-t px-5 py-2 text-xs text-muted-foreground">{status}</div>
    </div>
  );
});

function ensureMeasureTextWidth() {
  const target = globalThis as MeasureGlobal;
  if (target.measureTextWidth) {
    return;
  }
  let context: CanvasRenderingContext2D | null = null;
  let lastFont = "";
  target.measureTextWidth = (font, text) => {
    context ??= document.createElement("canvas").getContext("2d");
    if (!context) {
      return text.length * 10;
    }
    if (font !== lastFont) {
      context.font = font;
      lastFont = font;
    }
    return context.measureText(text).width;
  };
}

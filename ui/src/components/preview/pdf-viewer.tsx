import type { PDFDocumentProxy, PageViewport } from "pdfjs-dist";
import { memo, useEffect, useRef, useState } from "react";

import { PreviewToolbar } from "@/components/preview/preview-toolbar";
import { ScrollArea } from "@/components/ui/scroll-area";

type PdfDocument = PDFDocumentProxy;

export const PdfViewer = memo(function PdfViewer({
  sourceUrl,
}: {
  sourceUrl: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [document, setDocument] = useState<PdfDocument | null>(null);
  const [page, setPage] = useState(1);
  const [scale, setScale] = useState(1.25);
  const [status, setStatus] = useState("Loading PDF");

  useEffect(() => {
    let cancelled = false;
    let loadedDocument: PdfDocument | null = null;

    async function loadPdf() {
      setStatus("Loading PDF");
      setDocument(null);
      setPage(1);
      const [pdfjs, worker] = await Promise.all([
        import("pdfjs-dist"),
        import("pdfjs-dist/build/pdf.worker.mjs?url"),
      ]);
      pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
      const task = pdfjs.getDocument(sourceUrl);
      loadedDocument = await task.promise;
      if (cancelled) {
        loadedDocument.destroy();
        return;
      }
      setDocument(loadedDocument);
      setStatus("Ready");
    }

    loadPdf().catch((error: unknown) => {
      setStatus(error instanceof Error ? error.message : "PDF preview failed.");
    });

    return () => {
      cancelled = true;
      if (loadedDocument) {
        void loadedDocument.destroy();
      }
    };
  }, [sourceUrl]);

  useEffect(() => {
    let cancelled = false;
    async function renderPage() {
      if (!document || !canvasRef.current) {
        return;
      }
      const pdfPage = await document.getPage(page);
      if (cancelled || !canvasRef.current) {
        return;
      }
      const viewport: PageViewport = pdfPage.getViewport({ scale });
      const canvas = canvasRef.current;
      const context = canvas.getContext("2d");
      if (!context) {
        setStatus("Canvas is not available.");
        return;
      }
      canvas.width = Math.ceil(viewport.width);
      canvas.height = Math.ceil(viewport.height);
      await pdfPage.render({ canvas, canvasContext: context, viewport }).promise;
    }

    renderPage().catch((error: unknown) => {
      setStatus(error instanceof Error ? error.message : "PDF render failed.");
    });

    return () => {
      cancelled = true;
    };
  }, [document, page, scale]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PreviewToolbar
        canGoNext={Boolean(document && page < document.numPages)}
        canGoPrev={page > 1}
        page={page}
        pageCount={document?.numPages ?? 0}
        scale={scale}
        onNext={() =>
          setPage((current) => Math.min(current + 1, document?.numPages ?? current))
        }
        onPrev={() => setPage((current) => Math.max(current - 1, 1))}
        onZoomIn={() => setScale((current) => Math.min(current + 0.25, 3))}
        onZoomOut={() => setScale((current) => Math.max(current - 0.25, 0.5))}
      />
      <ScrollArea className="min-h-0 flex-1">
        <div className="flex min-h-full justify-center p-5">
          <canvas className="h-fit max-w-none border bg-card" ref={canvasRef} />
        </div>
      </ScrollArea>
      <div className="border-t px-5 py-2 text-xs text-muted-foreground">{status}</div>
    </div>
  );
});

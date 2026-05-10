import type { PageViewport } from "pdfjs-dist";
import { useEffect, useState } from "react";
import type { RefObject } from "react";

import type { PdfDocument, SlideViewport } from "./types";

export function usePptxPdf({
  canvasRef,
  scale,
  selectedSlideNumber,
  sourceUrl,
}: {
  canvasRef: RefObject<HTMLCanvasElement | null>;
  scale: number;
  selectedSlideNumber: number;
  sourceUrl: string;
}) {
  const [document, setDocument] = useState<PdfDocument | null>(null);
  const [slideViewport, setSlideViewport] = useState<SlideViewport | null>(null);
  const [status, setStatus] = useState("Loading deck");

  useEffect(() => {
    if (!sourceUrl) {
      return;
    }
    let cancelled = false;
    let loadedDocument: PdfDocument | null = null;

    async function loadPdf() {
      setStatus("Loading deck");
      setSlideViewport(null);
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
      setStatus(error instanceof Error ? error.message : "PPTX editor failed.");
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
    async function renderSlide() {
      if (!document || !canvasRef.current) {
        return;
      }
      const pdfPage = await document.getPage(selectedSlideNumber);
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
      setSlideViewport({ width: canvas.width, height: canvas.height });
      await pdfPage.render({ canvas, canvasContext: context, viewport }).promise;
    }

    renderSlide().catch((error: unknown) => {
      setStatus(error instanceof Error ? error.message : "Slide render failed.");
    });

    return () => {
      cancelled = true;
    };
  }, [canvasRef, document, scale, selectedSlideNumber]);

  return { document, slideViewport, status };
}

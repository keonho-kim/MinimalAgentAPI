import { memo, useCallback, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  FsPreviewResponse,
} from "@/lib/api";
import {
  applyPptxOperations,
  exportPptx,
  getPptxDeck,
} from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

import { PptxEditorToolbar } from "./pptx-editor-toolbar";
import { PptxInspector } from "./pptx-inspector";
import { operationsFromDraft } from "./pptx-operations";
import { PptxSlidePanel } from "./pptx-slide-panel";
import { PptxSlideStage } from "./pptx-slide-stage";
import { usePptxDraft } from "./use-pptx-draft";
import { usePptxPdf } from "./use-pptx-pdf";

const DEFAULT_CANVAS = { width: 9144000, height: 6858000 };

export const PptxEditor = memo(function PptxEditor({
  preview,
  sessionUuid,
  userId,
  onRefresh,
}: {
  preview: FsPreviewResponse;
  sessionUuid: string;
  userId: string;
  onRefresh: () => Promise<void> | void;
}) {
  const queryClient = useQueryClient();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [scale, setScale] = useState(1.05);
  const [pdfReloadKey, setPdfReloadKey] = useState(0);
  const [saveStatus, setSaveStatus] = useState("");
  const deckQuery = useQuery({
    queryKey: queryKeys.pptxDeck(userId, sessionUuid, preview.path),
    queryFn: () => getPptxDeck({ userId, sessionUuid, path: preview.path }),
  });
  const deck = deckQuery.data?.deck;
  const sourceUrl = useMemo(
    () => cacheBustedUrl(deckQuery.data?.source_url ?? preview.source_url ?? "", pdfReloadKey),
    [deckQuery.data?.source_url, pdfReloadKey, preview.source_url],
  );
  const slides = deck?.slides ?? [];
  const {
    draft,
    elements,
    redo,
    redoStack,
    selectElement,
    selectSlide,
    selectedElement,
    selectedElementId,
    selectedSlide,
    undo,
    undoStack,
    updateDraft,
  } = usePptxDraft(slides);
  const selectedSlideNumber = selectedSlide?.index ?? 1;
  const { document, slideViewport, status } = usePptxPdf({
    canvasRef,
    scale,
    selectedSlideNumber,
    sourceUrl,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!deck || !selectedElement || !draft || !selectedSlide) {
        return null;
      }
      const operations = operationsFromDraft(selectedElement, draft);
      if (operations.length === 0) {
        return null;
      }
      return applyPptxOperations({
        userId,
        sessionUuid,
        path: preview.path,
        expectedRevision: deck.revision,
        operations,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.pptxDeck(userId, sessionUuid, preview.path),
      });
      await onRefresh();
      setPdfReloadKey((current) => current + 1);
      setSaveStatus("Saved");
    },
    onError(error) {
      setSaveStatus(error instanceof Error ? error.message : "Save failed");
    },
  });
  const exportMutation = useMutation({
    mutationFn: (format: "pdf" | "pptx") =>
      exportPptx({ userId, sessionUuid, path: preview.path, format }),
    onSuccess(result) {
      setSaveStatus(`Exported ${result.filename}`);
    },
    onError(error) {
      setSaveStatus(error instanceof Error ? error.message : "Export failed");
    },
  });

  const handleSelectSlide = useCallback((slideId: string) => {
    selectSlide(slideId);
    setSaveStatus("");
  }, [selectSlide]);

  const handleSelectElement = useCallback((element: Parameters<typeof selectElement>[0]) => {
    selectElement(element);
    setSaveStatus("");
  }, [selectElement]);

  const handleDraftChange = useCallback((nextDraft: Parameters<typeof updateDraft>[0]) => {
    updateDraft(nextDraft);
    setSaveStatus("");
  }, [updateDraft]);

  if (deckQuery.isLoading) {
    return <div className="p-5 text-sm text-muted-foreground">Loading PPTX deck.</div>;
  }

  if (deckQuery.error || !deck) {
    return (
      <div className="p-5 text-sm text-destructive">
        {deckQuery.error instanceof Error
          ? deckQuery.error.message
          : "PPTX deck could not be loaded."}
      </div>
    );
  }

  if (!sourceUrl) {
    return (
      <div className="p-5 text-sm text-destructive">
        PPTX editor source is missing.
      </div>
    );
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[10rem_minmax(0,1fr)_16rem] bg-background">
      <PptxSlidePanel
        document={document}
        selectedSlideId={selectedSlide?.id ?? null}
        slides={slides}
        onSelectSlide={handleSelectSlide}
      />

      <section className="flex min-h-0 min-w-0 flex-col">
        <PptxEditorToolbar
          draft={draft}
          redoDisabled={redoStack.length === 0}
          savePending={saveMutation.isPending}
          scale={scale}
          selectedElement={selectedElement}
          selectedSlide={selectedSlide}
          slides={slides}
          undoDisabled={undoStack.length === 0}
          onNextSlide={() => {
            const next = slides[selectedSlideNumber];
            if (next) {
              handleSelectSlide(next.id);
            }
          }}
          onPreviousSlide={() => {
            const previous = slides[selectedSlideNumber - 2];
            if (previous) {
              handleSelectSlide(previous.id);
            }
          }}
          onRedo={redo}
          onSave={() => {
            setSaveStatus("Saving");
            saveMutation.mutate();
          }}
          onScaleChange={setScale}
          onUndo={undo}
        />
        <PptxSlideStage
          canvas={deck.canvas ?? DEFAULT_CANVAS}
          canvasRef={canvasRef}
          draft={draft}
          elements={elements}
          selectedElementId={selectedElementId}
          slideViewport={slideViewport}
          onDraftChange={handleDraftChange}
          onSelectElement={handleSelectElement}
        />
        <div className="border-t px-4 py-2 text-xs text-muted-foreground">
          {saveStatus || status}
        </div>
      </section>

      <PptxInspector
        draft={draft}
        exportPending={exportMutation.isPending}
        selectedElement={selectedElement}
        onExport={exportMutation.mutate}
      />
    </div>
  );
});

function cacheBustedUrl(sourceUrl: string, version: number) {
  if (!sourceUrl || version === 0) {
    return sourceUrl;
  }
  const separator = sourceUrl.includes("?") ? "&" : "?";
  return `${sourceUrl}${separator}pptx_editor_reload=${version}`;
}

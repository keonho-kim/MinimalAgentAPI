import { useCallback, useEffect, useState } from "react";

import type { PptxElement, PptxSlide } from "@/lib/api";

import { draftFromElement } from "./pptx-slide-stage";
import type { PptxTextShapeDraft } from "./types";

export function usePptxDraft(slides: PptxSlide[]) {
  const [selectedSlideId, setSelectedSlideId] = useState<string | null>(null);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [draft, setDraft] = useState<PptxTextShapeDraft | null>(null);
  const [undoStack, setUndoStack] = useState<PptxTextShapeDraft[]>([]);
  const [redoStack, setRedoStack] = useState<PptxTextShapeDraft[]>([]);
  const selectedSlide =
    slides.find((slide) => slide.id === selectedSlideId) ?? slides[0] ?? null;
  const elements = selectedSlide?.elements ?? [];
  const selectedElement =
    elements.find((element) => element.id === selectedElementId) ??
    elements[0] ??
    null;

  useEffect(() => {
    if (!selectedSlideId && slides[0]) {
      setSelectedSlideId(slides[0].id);
    }
  }, [selectedSlideId, slides]);

  useEffect(() => {
    setSelectedElementId(elements[0]?.id ?? null);
  }, [selectedSlide?.id, elements]);

  useEffect(() => {
    setDraft(selectedElement ? draftFromElement(selectedElement) : null);
    setUndoStack([]);
    setRedoStack([]);
  }, [selectedElement]);

  const selectSlide = useCallback((slideId: string) => {
    setSelectedSlideId(slideId);
  }, []);

  const selectElement = useCallback((element: PptxElement) => {
    setSelectedElementId(element.id);
    setDraft(draftFromElement(element));
    setUndoStack([]);
    setRedoStack([]);
  }, []);

  const updateDraft = useCallback((nextDraft: PptxTextShapeDraft) => {
    setDraft((current) => {
      if (current) {
        setUndoStack((stack) => [...stack.slice(-19), current]);
      }
      return nextDraft;
    });
    setRedoStack([]);
  }, []);

  const undo = useCallback(() => {
    setUndoStack((stack) => {
      const previous = stack.at(-1);
      if (!previous) {
        return stack;
      }
      setDraft((current) => {
        if (current) {
          setRedoStack((redo) => [...redo, current]);
        }
        return previous;
      });
      return stack.slice(0, -1);
    });
  }, []);

  const redo = useCallback(() => {
    setRedoStack((stack) => {
      const next = stack.at(-1);
      if (!next) {
        return stack;
      }
      setDraft((current) => {
        if (current) {
          setUndoStack((undoItems) => [...undoItems, current]);
        }
        return next;
      });
      return stack.slice(0, -1);
    });
  }, []);

  return {
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
  };
}

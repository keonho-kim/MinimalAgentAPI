import type { PptxElement, PptxOperation } from "@/lib/api";

import type { PptxTextShapeDraft } from "./types";

export function operationsFromDraft(
  element: PptxElement,
  draft: PptxTextShapeDraft,
): PptxOperation[] {
  const operations: PptxOperation[] = [];
  if (element.type === "text" && draft.text !== element.content) {
    operations.push({
      type: "updateText",
      slideId: element.slideId,
      elementId: element.id,
      content: draft.text,
    });
  }
  if (draft.x !== element.x || draft.y !== element.y) {
    operations.push({
      type: "moveElement",
      slideId: element.slideId,
      elementId: element.id,
      x: draft.x,
      y: draft.y,
    });
  }
  if (draft.width !== element.width || draft.height !== element.height) {
    operations.push({
      type: "resizeElement",
      slideId: element.slideId,
      elementId: element.id,
      width: draft.width,
      height: draft.height,
    });
  }
  return operations;
}

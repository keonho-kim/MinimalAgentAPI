import type {
  CSSProperties,
  PointerEvent as ReactPointerEvent,
  RefObject,
} from "react";
import { useEffect, useMemo, useState } from "react";

import type { PptxDeck, PptxElement } from "@/lib/api";
import { cn } from "@/lib/utils";

import type { PptxTextShapeDraft, SlideViewport } from "./types";

type Interaction = {
  mode: "move" | "resize";
  startX: number;
  startY: number;
  startDraft: PptxTextShapeDraft;
};

export function PptxSlideStage({
  canvasRef,
  canvas,
  draft,
  elements,
  selectedElementId,
  slideViewport,
  onDraftChange,
  onSelectElement,
}: {
  canvasRef: RefObject<HTMLCanvasElement | null>;
  canvas: PptxDeck["canvas"];
  draft: PptxTextShapeDraft | null;
  elements: PptxElement[];
  selectedElementId: string | null;
  slideViewport: SlideViewport | null;
  onDraftChange: (draft: PptxTextShapeDraft) => void;
  onSelectElement: (element: PptxElement) => void;
}) {
  const [interaction, setInteraction] = useState<Interaction | null>(null);
  const [editingElementId, setEditingElementId] = useState<string | null>(null);
  const scale = useMemo(() => {
    if (!slideViewport) {
      return { x: 1, y: 1 };
    }
    return {
      x: slideViewport.width / canvas.width,
      y: slideViewport.height / canvas.height,
    };
  }, [canvas.height, canvas.width, slideViewport]);

  useEffect(() => {
    if (!interaction || !slideViewport) {
      return;
    }
    const activeInteraction = interaction;

    function updateDraft(event: PointerEvent) {
      const deltaX = Math.round((event.clientX - activeInteraction.startX) / scale.x);
      const deltaY = Math.round((event.clientY - activeInteraction.startY) / scale.y);
      const draft =
        activeInteraction.mode === "move"
          ? moveDraft(activeInteraction.startDraft, deltaX, deltaY, canvas)
          : resizeDraft(activeInteraction.startDraft, deltaX, deltaY, canvas);
      onDraftChange(draft);
    }

    function finishInteraction() {
      setInteraction(null);
    }

    window.addEventListener("pointermove", updateDraft);
    window.addEventListener("pointerup", finishInteraction, { once: true });
    return () => {
      window.removeEventListener("pointermove", updateDraft);
      window.removeEventListener("pointerup", finishInteraction);
    };
  }, [canvas, interaction, onDraftChange, scale, slideViewport]);

  return (
    <div className="min-h-0 flex-1 overflow-auto bg-muted/30">
      <div className="flex min-h-full justify-center p-6">
        <div
          className="relative h-fit border bg-card shadow-sm"
          style={slideViewportStyle(slideViewport)}
        >
          <canvas className="block" ref={canvasRef} />
          {slideViewport
            ? elements.map((element) => {
                const selected = element.id === selectedElementId;
                const editing = element.id === editingElementId;
                const displayDraft =
                  selected && draft ? draft : draftFromElement(element);
                return (
                  <div
                    className={cn(
                      "absolute outline-none transition-colors",
                      selected
                        ? "border border-foreground ring-2 ring-ring"
                        : "border border-transparent hover:border-foreground/30",
                    )}
                    key={element.id}
                    role="button"
                    style={elementStyle({
                      draft: displayDraft,
                      canvas,
                      editing,
                      selected,
                      viewport: slideViewport,
                    })}
                    tabIndex={0}
                    onClick={() => onSelectElement(element)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        onSelectElement(element);
                      }
                    }}
                    onPointerDown={(event) => {
                      if (!selected) {
                        onSelectElement(element);
                        return;
                      }
                      if (event.target instanceof HTMLTextAreaElement) {
                        return;
                      }
                      startInteraction(event, "move", displayDraft);
                    }}
                  >
                    {element.type === "text" ? (
                      <textarea
                        aria-label={elementLabel(element)}
                        className={cn(
                          "size-full resize-none overflow-hidden px-2 py-1 text-sm leading-tight outline-none",
                          editing
                            ? "cursor-text bg-background text-foreground shadow-sm"
                            : "cursor-text bg-transparent text-transparent",
                        )}
                        readOnly={!selected}
                        spellCheck={false}
                        value={displayDraft.text}
                        onChange={(event) =>
                          onDraftChange({ ...displayDraft, text: event.target.value })
                        }
                        onFocus={() => {
                          onSelectElement(element);
                          setEditingElementId(element.id);
                        }}
                        onBlur={() => {
                          setEditingElementId((current) =>
                            current === element.id ? null : current,
                          );
                        }}
                      />
                    ) : (
                      <div className="size-full bg-transparent" />
                    )}
                    {selected ? (
                      <button
                        aria-label="Resize element"
                        className="absolute -bottom-1.5 -right-1.5 size-3 rounded-sm border border-foreground bg-background"
                        type="button"
                        onPointerDown={(event) => {
                          event.stopPropagation();
                          startInteraction(event, "resize", displayDraft);
                        }}
                      />
                    ) : null}
                  </div>
                );
              })
            : null}
        </div>
      </div>
    </div>
  );

  function startInteraction(
    event: ReactPointerEvent,
    mode: Interaction["mode"],
    startDraft: PptxTextShapeDraft,
  ) {
    event.preventDefault();
    setInteraction({
      mode,
      startX: event.clientX,
      startY: event.clientY,
      startDraft,
    });
  }
}

export function draftFromElement(element: PptxElement): PptxTextShapeDraft {
  return {
    element,
    text: element.content,
    x: element.x,
    y: element.y,
    width: element.width,
    height: element.height,
  };
}

function elementStyle({
  draft,
  canvas,
  editing,
  selected,
  viewport,
}: {
  draft: PptxTextShapeDraft;
  canvas: PptxDeck["canvas"];
  editing: boolean;
  selected: boolean;
  viewport: SlideViewport;
}): CSSProperties {
  const scaleX = viewport.width / canvas.width;
  const scaleY = viewport.height / canvas.height;
  const height = Math.max(24, draft.height * scaleY);
  return {
    cursor: editing ? "text" : selected ? "move" : "default",
    fontSize: `${Math.max(11, Math.min(28, height * 0.32))}px`,
    height: `${height}px`,
    left: `${draft.x * scaleX}px`,
    top: `${draft.y * scaleY}px`,
    width: `${Math.max(32, draft.width * scaleX)}px`,
  };
}

function slideViewportStyle(viewport: SlideViewport | null): CSSProperties {
  if (!viewport) {
    return {};
  }
  return {
    minHeight: `${viewport.height}px`,
    minWidth: `${viewport.width}px`,
  };
}

function moveDraft(
  draft: PptxTextShapeDraft,
  deltaX: number,
  deltaY: number,
  canvas: PptxDeck["canvas"],
) {
  return {
    ...draft,
    x: clamp(draft.x + deltaX, 0, Math.max(0, canvas.width - draft.width)),
    y: clamp(draft.y + deltaY, 0, Math.max(0, canvas.height - draft.height)),
  };
}

function resizeDraft(
  draft: PptxTextShapeDraft,
  deltaX: number,
  deltaY: number,
  canvas: PptxDeck["canvas"],
) {
  return {
    ...draft,
    width: clamp(draft.width + deltaX, 91440, Math.max(91440, canvas.width - draft.x)),
    height: clamp(
      draft.height + deltaY,
      91440,
      Math.max(91440, canvas.height - draft.y),
    ),
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function elementLabel(element: PptxElement) {
  return `${element.role || element.type} ${element.id}`;
}

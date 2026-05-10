import { Download } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { PptxElement } from "@/lib/api";

import type { PptxTextShapeDraft } from "./types";

export function PptxInspector({
  draft,
  exportPending,
  selectedElement,
  onExport,
}: {
  draft: PptxTextShapeDraft | null;
  exportPending: boolean;
  selectedElement: PptxElement | null;
  onExport(format: "pdf" | "pptx"): void;
}) {
  return (
    <aside className="min-h-0 border-l bg-card p-4">
      <div className="flex h-full flex-col gap-4">
        <div>
          <h3 className="text-sm font-medium">Element</h3>
          <p className="mt-1 break-all text-xs text-muted-foreground">
            {selectedElement?.id ?? "No selection"}
          </p>
        </div>
        {selectedElement && draft ? (
          <dl className="grid grid-cols-2 gap-2 text-xs">
            <dt className="text-muted-foreground">Type</dt>
            <dd>{selectedElement.type}</dd>
            <dt className="text-muted-foreground">X</dt>
            <dd>{draft.x}</dd>
            <dt className="text-muted-foreground">Y</dt>
            <dd>{draft.y}</dd>
            <dt className="text-muted-foreground">W</dt>
            <dd>{draft.width}</dd>
            <dt className="text-muted-foreground">H</dt>
            <dd>{draft.height}</dd>
          </dl>
        ) : null}
        <div className="mt-auto flex flex-col gap-2">
          <Button
            disabled={exportPending}
            size="sm"
            type="button"
            variant="outline"
            onClick={() => onExport("pdf")}
          >
            <Download data-icon="inline-start" />
            PDF export
          </Button>
          <Button
            disabled={exportPending}
            size="sm"
            type="button"
            variant="outline"
            onClick={() => onExport("pptx")}
          >
            <Download data-icon="inline-start" />
            PPTX export
          </Button>
        </div>
      </div>
    </aside>
  );
}

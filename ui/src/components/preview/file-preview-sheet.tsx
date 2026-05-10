import { RefreshCw } from "lucide-react";
import { memo } from "react";

import type { FsPreviewResponse } from "@/lib/api";
import { CodePreview } from "@/components/preview/code-preview";
import { HwpxViewer } from "@/components/preview/hwpx-viewer";
import { PdfViewer } from "@/components/preview/pdf-viewer";
import { PptxEditor } from "@/components/preview/pptx/pptx-editor";
import { TextPreview } from "@/components/preview/text-preview";
import { XlsxGrid } from "@/components/preview/xlsx-grid";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

type FilePreviewSheetProps = {
  open: boolean;
  preview: FsPreviewResponse | null;
  status: string;
  onOpenChange: (open: boolean) => void;
  onRefresh: () => void;
  sessionUuid: string;
  userId: string;
};

export const FilePreviewSheet = memo(function FilePreviewSheet({
  open,
  preview,
  status,
  sessionUuid,
  userId,
  onOpenChange,
  onRefresh,
}: FilePreviewSheetProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex max-w-5xl flex-col p-0">
        <SheetHeader className="border-b px-5 py-4">
          <div className="flex items-start justify-between gap-4 pr-9">
            <div className="min-w-0">
              <SheetTitle className="truncate">
                {preview?.filename ?? "File preview"}
              </SheetTitle>
              <SheetDescription className="truncate">{status}</SheetDescription>
            </div>
            <Button size="sm" variant="outline" onClick={onRefresh}>
              <RefreshCw data-icon="inline-start" />
              Refresh
            </Button>
          </div>
        </SheetHeader>
        <div className="min-h-0 flex-1 bg-background">
          <PreviewContent
            preview={preview}
            sessionUuid={sessionUuid}
            userId={userId}
            onRefresh={onRefresh}
          />
        </div>
      </SheetContent>
    </Sheet>
  );
});

function PreviewContent({
  preview,
  sessionUuid,
  userId,
  onRefresh,
}: {
  preview: FsPreviewResponse | null;
  sessionUuid: string;
  userId: string;
  onRefresh: () => void;
}) {
  if (!preview) {
    return (
      <div className="p-5 text-sm text-muted-foreground">
        Select a supported file to preview.
      </div>
    );
  }

  if (preview.preview_type === "xlsx_grid" && preview.workbook) {
    return <XlsxGrid workbook={preview.workbook.sheets} />;
  }

  if (preview.preview_type === "hwpx" && preview.source_url) {
    return <HwpxViewer sourceUrl={preview.source_url} />;
  }

  if (preview.preview_type === "markdown" && preview.source_url) {
    return <TextPreview mode="markdown" sourceUrl={preview.source_url} />;
  }

  if (preview.preview_type === "text" && preview.source_url) {
    return <TextPreview mode="text" sourceUrl={preview.source_url} />;
  }

  if (preview.preview_type === "code" && preview.source_url) {
    return <CodePreview filename={preview.filename} sourceUrl={preview.source_url} />;
  }

  if (preview.file_type === "pptx" && preview.source_url) {
    return (
      <PptxEditor
        preview={preview}
        sessionUuid={sessionUuid}
        userId={userId}
        onRefresh={onRefresh}
      />
    );
  }

  if (preview.source_url) {
    return <PdfViewer sourceUrl={preview.source_url} />;
  }

  return <div className="p-5 text-sm text-destructive">Preview source is missing.</div>;
}

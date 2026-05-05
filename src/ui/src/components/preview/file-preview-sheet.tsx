import DOMPurify from "dompurify";
import { ChevronLeft, ChevronRight, RefreshCw, ZoomIn, ZoomOut } from "lucide-react";
import type { PDFDocumentProxy, PageViewport } from "pdfjs-dist";
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";

import type { FsPreviewResponse, XlsxCell, XlsxSheet } from "@/lib/api";
import {
  codeLanguageLabel,
  highlightCode,
  languageForFilename,
} from "@/lib/code-highlight";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
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
};

type PdfDocument = PDFDocumentProxy;

type RhwpDocument = {
  pageCount: () => number;
  renderPageSvg: (pageIndex: number) => string;
};

type MeasureGlobal = typeof globalThis & {
  measureTextWidth?: (font: string, text: string) => number;
};

const MessageRenderer = lazy(() =>
  import("@/components/message-renderer").then((module) => ({
    default: module.MessageRenderer,
  })),
);

export function FilePreviewSheet({
  open,
  preview,
  status,
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
          {!preview ? (
            <div className="p-5 text-sm text-muted-foreground">
              Select a supported file to preview.
            </div>
          ) : preview.preview_type === "xlsx_grid" && preview.workbook ? (
            <XlsxGrid workbook={preview.workbook.sheets} />
          ) : preview.preview_type === "hwpx" && preview.source_url ? (
            <HwpxViewer sourceUrl={preview.source_url} />
          ) : preview.preview_type === "markdown" && preview.source_url ? (
            <TextPreview mode="markdown" sourceUrl={preview.source_url} />
          ) : preview.preview_type === "text" && preview.source_url ? (
            <TextPreview mode="text" sourceUrl={preview.source_url} />
          ) : preview.preview_type === "code" && preview.source_url ? (
            <CodePreview filename={preview.filename} sourceUrl={preview.source_url} />
          ) : preview.source_url ? (
            <PdfViewer sourceUrl={preview.source_url} />
          ) : (
            <div className="p-5 text-sm text-destructive">
              Preview source is missing.
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function TextPreview({
  sourceUrl,
  mode,
}: {
  sourceUrl: string;
  mode: "markdown" | "text";
}) {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState("Loading text");

  useEffect(() => {
    let cancelled = false;

    async function loadText() {
      setStatus("Loading text");
      setContent("");
      const response = await fetch(sourceUrl);
      if (!response.ok) {
        throw new Error(`Text source failed: ${response.status}`);
      }
      const text = await response.text();
      if (cancelled) {
        return;
      }
      setContent(text);
      setStatus("Ready");
    }

    loadText().catch((error: unknown) => {
      setStatus(error instanceof Error ? error.message : "Text preview failed.");
    });

    return () => {
      cancelled = true;
    };
  }, [sourceUrl]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ScrollArea className="min-h-0 flex-1">
        <div className="mx-auto max-w-4xl p-5">
          {mode === "markdown" ? (
            <div className="rounded-md border bg-card p-5">
              <Suspense
                fallback={
                  <div className="message-renderer whitespace-pre-wrap">{content}</div>
                }
              >
                <MessageRenderer content={content} role="assistant" />
              </Suspense>
            </div>
          ) : (
            <pre className="min-h-80 whitespace-pre-wrap rounded-md border bg-card p-5 font-mono text-sm leading-6 text-foreground">
              {content}
            </pre>
          )}
        </div>
      </ScrollArea>
      <div className="border-t px-5 py-2 text-xs text-muted-foreground">{status}</div>
    </div>
  );
}

function CodePreview({
  sourceUrl,
  filename,
}: {
  sourceUrl: string;
  filename: string;
}) {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState("Loading code");
  const language = languageForFilename(filename);
  const highlighted = useMemo(
    () => DOMPurify.sanitize(highlightCode(content, language), {
      USE_PROFILES: { html: true },
      ADD_ATTR: ["class"],
    }),
    [content, language],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadCode() {
      setStatus("Loading code");
      setContent("");
      const response = await fetch(sourceUrl);
      if (!response.ok) {
        throw new Error(`Code source failed: ${response.status}`);
      }
      const text = await response.text();
      if (cancelled) {
        return;
      }
      setContent(text);
      setStatus("Ready");
    }

    loadCode().catch((error: unknown) => {
      setStatus(error instanceof Error ? error.message : "Code preview failed.");
    });

    return () => {
      cancelled = true;
    };
  }, [sourceUrl]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between border-b bg-card px-5 py-3">
        <span className="truncate font-mono text-sm text-muted-foreground">
          {filename}
        </span>
        <span className="rounded-md border bg-background px-2 py-1 text-xs font-medium text-muted-foreground">
          {codeLanguageLabel(language)}
        </span>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="p-5">
          <pre className="overflow-x-auto rounded-md border bg-card p-5 text-sm leading-6">
            <code
              className={cn("hljs block min-w-max font-mono", {
                [`language-${language}`]: Boolean(language),
              })}
              dangerouslySetInnerHTML={{ __html: highlighted }}
            />
          </pre>
        </div>
      </ScrollArea>
      <div className="border-t px-5 py-2 text-xs text-muted-foreground">{status}</div>
    </div>
  );
}

function PdfViewer({ sourceUrl }: { sourceUrl: string }) {
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
        onNext={() => setPage((current) => Math.min(current + 1, document?.numPages ?? current))}
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
}

function HwpxViewer({ sourceUrl }: { sourceUrl: string }) {
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
        onNext={() => setPage((current) => Math.min(current + 1, document?.pageCount() ?? current))}
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
}

function XlsxGrid({ workbook }: { workbook: XlsxSheet[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const sheet = workbook[activeIndex] ?? workbook[0];
  const cellMap = useMemo(() => buildCellMap(sheet), [sheet]);

  if (!sheet) {
    return <div className="p-5 text-sm text-muted-foreground">Workbook is empty.</div>;
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ScrollArea className="min-h-0 flex-1">
        <div className="p-4">
          <table className="border-collapse bg-card text-sm">
            <thead>
              <tr>
                <th className="sticky left-0 top-0 z-20 size-8 border bg-muted" />
                {sheet.columns.map((column) => (
                  <th
                    className="sticky top-0 z-10 border bg-muted px-2 text-center text-xs font-medium text-muted-foreground"
                    key={column.index}
                    style={{ minWidth: column.width, width: column.width }}
                  >
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sheet.rows.map((row) => (
                <tr key={row.index} style={{ height: row.height }}>
                  <th className="sticky left-0 z-10 border bg-muted px-2 text-right text-xs font-medium text-muted-foreground">
                    {row.index}
                  </th>
                  {sheet.columns.map((column) => {
                    const address = `${column.label}${row.index}`;
                    const merge = cellMap.merges.get(address);
                    if (merge?.covered) {
                      return null;
                    }
                    const cell = cellMap.cells.get(address);
                    return (
                      <td
                        className={cn(
                          "max-w-64 overflow-hidden text-ellipsis whitespace-nowrap border px-2 text-foreground",
                          cell?.style.bold ? "font-semibold" : "",
                          cell?.style.italic ? "italic" : "",
                        )}
                        colSpan={merge?.colSpan}
                        key={address}
                        rowSpan={merge?.rowSpan}
                        style={{
                          backgroundColor: cell?.style.background,
                          color: cell?.style.color,
                          textAlign: textAlign(cell),
                          minWidth: column.width,
                          width: column.width,
                        }}
                        title={cellTitle(cell)}
                      >
                        {cellDisplay(cell)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ScrollArea>
      <div className="flex min-h-11 items-end gap-1 overflow-x-auto border-t bg-card px-3 pt-2">
        {workbook.map((item, index) => (
          <button
            className={cn(
              "min-w-24 rounded-t-md border border-b-0 px-3 py-2 text-sm",
              index === activeIndex
                ? "bg-background text-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground",
            )}
            key={item.id}
            onClick={() => setActiveIndex(index)}
            type="button"
          >
            <span className="block truncate">{item.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function PreviewToolbar({
  page,
  pageCount,
  scale,
  canGoPrev,
  canGoNext,
  onPrev,
  onNext,
  onZoomOut,
  onZoomIn,
}: {
  page: number;
  pageCount: number;
  scale: number;
  canGoPrev: boolean;
  canGoNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  onZoomOut: () => void;
  onZoomIn: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b bg-card px-5 py-3">
      <div className="flex items-center gap-1">
        <Button disabled={!canGoPrev} size="icon" variant="outline" onClick={onPrev}>
          <ChevronLeft data-icon="inline-start" />
          <span className="sr-only">Previous page</span>
        </Button>
        <Button disabled={!canGoNext} size="icon" variant="outline" onClick={onNext}>
          <ChevronRight data-icon="inline-start" />
          <span className="sr-only">Next page</span>
        </Button>
        <span className="px-2 text-sm text-muted-foreground">
          {pageCount ? `${page} / ${pageCount}` : "Loading"}
        </span>
      </div>
      <div className="flex items-center gap-1">
        <Button size="icon" variant="outline" onClick={onZoomOut}>
          <ZoomOut data-icon="inline-start" />
          <span className="sr-only">Zoom out</span>
        </Button>
        <span className="w-14 text-center text-sm text-muted-foreground">
          {Math.round(scale * 100)}%
        </span>
        <Button size="icon" variant="outline" onClick={onZoomIn}>
          <ZoomIn data-icon="inline-start" />
          <span className="sr-only">Zoom in</span>
        </Button>
      </div>
    </div>
  );
}

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

function buildCellMap(sheet: XlsxSheet) {
  const cells = new Map(sheet.cells.map((cell) => [cell.address, cell]));
  const merges = new Map<
    string,
    { rowSpan?: number; colSpan?: number; covered?: boolean }
  >();

  for (const range of sheet.merged_ranges) {
    const parsed = parseRange(range);
    if (!parsed) {
      continue;
    }
    const rowSpan = parsed.endRow - parsed.startRow + 1;
    const colSpan = parsed.endColumn - parsed.startColumn + 1;
    for (let row = parsed.startRow; row <= parsed.endRow; row += 1) {
      for (let column = parsed.startColumn; column <= parsed.endColumn; column += 1) {
        const address = `${columnLabel(column)}${row}`;
        merges.set(
          address,
          row === parsed.startRow && column === parsed.startColumn
            ? { rowSpan, colSpan }
            : { covered: true },
        );
      }
    }
  }

  return { cells, merges };
}

function parseRange(range: string) {
  const match = /^([A-Z]+)(\d+):([A-Z]+)(\d+)$/.exec(range);
  if (!match) {
    return null;
  }
  return {
    startColumn: columnIndex(match[1]),
    startRow: Number(match[2]),
    endColumn: columnIndex(match[3]),
    endRow: Number(match[4]),
  };
}

function columnIndex(label: string) {
  return [...label].reduce((total, character) => {
    return total * 26 + character.charCodeAt(0) - 64;
  }, 0);
}

function columnLabel(index: number) {
  let value = index;
  let label = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    value = Math.floor((value - 1) / 26);
  }
  return label;
}

function cellDisplay(cell?: XlsxCell) {
  if (!cell) {
    return "";
  }
  if (cell.value === null) {
    return cell.formula ?? "";
  }
  return String(cell.value);
}

function cellTitle(cell?: XlsxCell) {
  if (!cell) {
    return "";
  }
  return cell.formula ? `${cell.address} ${cell.formula}` : `${cell.address} ${cellDisplay(cell)}`;
}

function textAlign(cell?: XlsxCell) {
  if (cell?.style.horizontal === "center") {
    return "center";
  }
  if (cell?.style.horizontal === "right") {
    return "right";
  }
  return typeof cell?.value === "number" ? "right" : "left";
}

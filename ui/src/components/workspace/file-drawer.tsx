import { Eye, FileText, RefreshCw, Upload } from "lucide-react";
import type { FormEvent } from "react";

import type { FsListItem } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function FileDrawer({
  open,
  files,
  status,
  onOpenChange,
  onRefresh,
  onUpload,
  onPreview,
  isPreviewSupported,
}: {
  open: boolean;
  files: FsListItem[];
  status: string;
  onOpenChange(open: boolean): void;
  onRefresh(): void;
  onUpload(event: FormEvent<HTMLFormElement>): void;
  onPreview(file: FsListItem): void;
  isPreviewSupported(filename: string): boolean;
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Workspace Files</SheetTitle>
          <SheetDescription>{status}</SheetDescription>
        </SheetHeader>
        <form className="mt-5 grid gap-2" onSubmit={onUpload}>
          <Input name="files" type="file" multiple />
          <Button type="submit">
            <Upload data-icon="inline-start" />
            Upload
          </Button>
        </form>
        <Button className="mt-3 w-full" variant="outline" onClick={onRefresh}>
          <RefreshCw data-icon="inline-start" />
          Refresh
        </Button>
        <div className="mt-5 flex flex-col gap-2">
          {files.length === 0 ? (
            <div className="rounded-lg border border-dashed bg-background p-4 text-sm text-muted-foreground">
              No visible files.
            </div>
          ) : (
            files.map((file) => (
              <Card key={file.path} className="bg-background">
                <CardContent className="flex items-center gap-3 p-3">
                  <FileText className="text-muted-foreground" data-icon="inline-start" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground">{file.type}</p>
                  </div>
                  {file.type === "file" && isPreviewSupported(file.name) ? (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="icon"
                          variant="ghost"
                          onClick={() => {
                            onPreview(file);
                          }}
                        >
                          <Eye data-icon="inline-start" />
                          <span className="sr-only">Preview</span>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Preview</TooltipContent>
                    </Tooltip>
                  ) : null}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

import { Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { hasDraggedFiles } from "./file-drawer-utils";

export function FileDrawerUpload({
  onUploadFiles,
}: {
  onUploadFiles(files: File[]): Promise<void>;
}) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const uploadFileList = useCallback(
    async (fileList: File[]) => {
      if (!fileList.length) {
        return;
      }
      await onUploadFiles(fileList);
    },
    [onUploadFiles],
  );

  const handleFileInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const nextFiles = Array.from(event.target.files ?? []);
      event.target.value = "";
      void uploadFileList(nextFiles);
    },
    [uploadFileList],
  );

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    if (!hasDraggedFiles(event)) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.stopPropagation();
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>) => {
      if (!hasDraggedFiles(event)) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      setDragActive(false);
      void uploadFileList(Array.from(event.dataTransfer.files));
    },
    [uploadFileList],
  );

  return (
    <>
      <input
        className="hidden"
        multiple
        ref={fileInputRef}
        type="file"
        onChange={handleFileInputChange}
      />
      <div
        className={cn(
          "mt-5 rounded-lg border border-dashed bg-background p-3 transition-colors",
          dragActive && "border-ring bg-accent/40",
        )}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <Button
          className="mx-auto flex w-full max-w-[16rem]"
          type="button"
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload data-icon="inline-start" />
          업로드
        </Button>
        <p className="mt-2 text-center text-xs text-muted-foreground">
          여기에 파일을 놓으면 업로드됩니다.
        </p>
      </div>
    </>
  );
}

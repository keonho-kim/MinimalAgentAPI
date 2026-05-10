import { useCallback, useState } from "react";
import type { DragEvent } from "react";

import type { ComposerEditorHandle } from "@/lib/composer-editor";
import {
  fileMentionAttachmentFromDragPayload,
  readFileMentionDragPayload,
} from "@/lib/file-mentions";

export function useGlobalFileDrop({
  composerRef,
  disabled,
  uploadFiles,
}: {
  composerRef: { current: ComposerEditorHandle | null };
  disabled: boolean;
  uploadFiles(files: File[]): Promise<void>;
}) {
  const [dropActive, setDropActive] = useState(false);

  const handleDragOver = useCallback(
    (event: DragEvent<HTMLElement>) => {
      if (
        (!hasDraggedFiles(event) && !hasDraggedFileMention(event)) ||
        disabled
      ) {
        return;
      }
      event.preventDefault();
      if (hasDraggedFiles(event)) {
        setDropActive(true);
      }
    },
    [disabled],
  );

  const handleDragLeave = useCallback((event: DragEvent<HTMLElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setDropActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLElement>) => {
      const fileMentionPayload = readFileMentionDragPayload(event.dataTransfer);
      if (fileMentionPayload) {
        event.preventDefault();
        setDropActive(false);
        if (!disabled) {
          composerRef.current?.insertFileMentions([
            fileMentionAttachmentFromDragPayload(fileMentionPayload),
          ]);
        }
        return;
      }

      if (!hasDraggedFiles(event)) {
        return;
      }
      event.preventDefault();
      setDropActive(false);
      if (disabled) {
        return;
      }
      void uploadFiles(Array.from(event.dataTransfer.files));
    },
    [composerRef, disabled, uploadFiles],
  );

  return {
    dropActive,
    handleDragLeave,
    handleDragOver,
    handleDrop,
  };
}

function hasDraggedFiles(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.types).includes("Files");
}

function hasDraggedFileMention(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.types).includes(
    "application/x-minimal-agent-file",
  );
}

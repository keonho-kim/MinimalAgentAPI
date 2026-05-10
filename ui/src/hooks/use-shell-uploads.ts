import { useCallback, useState } from "react";

import type { ComposerEditorHandle } from "@/lib/composer-editor";
import type { UploadResponse } from "@/lib/api";
import { toAgentFileHref } from "@/lib/file-mentions";
import { createId } from "@/lib/id";

export function useShellUploads({
  composerRef,
  uploadSelectedFiles,
}: {
  composerRef: { current: ComposerEditorHandle | null };
  uploadSelectedFiles(files: File[]): Promise<UploadResponse>;
}) {
  const [uploadError, setUploadError] = useState<string | null>(null);

  const uploadFiles = useCallback(
    async (
      files: File[],
      { insertIntoComposer }: { insertIntoComposer: boolean },
    ) => {
      setUploadError(null);
      try {
        const response = await uploadSelectedFiles(files);
        const results = response.uploaded_files.map((file, index) => ({
          ...file,
          originalName: files[index]?.name ?? file.filename,
        }));
        const uploaded = results.filter(
          (file): file is typeof file & { path: string } =>
            file.status === "converted" && Boolean(file.path),
        );
        const failed = results.filter(
          (file) => file.status !== "converted" || !file.path,
        );

        if (insertIntoComposer && uploaded.length) {
          composerRef.current?.insertFileMentions(
            uploaded.map((file) => ({
              id: createId(),
              label: file.originalName,
              href: toAgentFileHref(file.path),
            })),
          );
        }

        if (failed.length) {
          setUploadError("하나 이상의 파일 업로드에 실패했습니다.");
        }
      } catch {
        setUploadError("업로드에 실패했습니다.");
      }
    },
    [composerRef, uploadSelectedFiles],
  );

  const uploadComposerFiles = useCallback(
    (files: File[]) => uploadFiles(files, { insertIntoComposer: true }),
    [uploadFiles],
  );

  const uploadDrawerFiles = useCallback(
    (files: File[]) => uploadFiles(files, { insertIntoComposer: false }),
    [uploadFiles],
  );

  const clearUploadError = useCallback(() => {
    setUploadError(null);
  }, []);

  return {
    clearUploadError,
    uploadComposerFiles,
    uploadDrawerFiles,
    uploadError,
  };
}

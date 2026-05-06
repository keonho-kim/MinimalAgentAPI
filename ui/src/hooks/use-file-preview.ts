import { useCallback, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import type { FsListItem } from "@/lib/api";
import { getFilePreview } from "@/lib/api";
import { isPreviewSupported } from "@/lib/preview-support";
import { queryKeys } from "@/lib/query-keys";

export function useFilePreview({
  userId,
  sessionUuid,
}: {
  userId: string;
  sessionUuid: string;
}) {
  const [open, setOpen] = useState(false);
  const [activeFile, setActiveFile] = useState<FsListItem | null>(null);
  const activePath = activeFile?.path ?? "";
  const previewQuery = useQuery({
    queryKey: queryKeys.filePreview(userId, sessionUuid, activePath),
    queryFn: () =>
      getFilePreview({
        userId,
        sessionUuid,
        path: activePath,
      }),
    enabled: Boolean(open && activePath),
  });
  const { refetch } = previewQuery;

  const openPreview = useCallback((file: FsListItem) => {
    if (file.type !== "file" || !isPreviewSupported(file.name)) {
      return;
    }
    setActiveFile(file);
    setOpen(true);
  }, []);

  const refresh = useCallback(async () => {
    if (!activePath) {
      return;
    }
    await refetch();
  }, [activePath, refetch]);

  return {
    open,
    openPreview,
    preview: previewQuery.data ?? null,
    refresh,
    setOpen,
    status: previewStatus(previewQuery),
  };
}

function previewStatus(previewQuery: {
  error: unknown;
  isFetching: boolean;
}) {
  if (previewQuery.isFetching) {
    return "Loading";
  }
  if (previewQuery.error) {
    return previewQuery.error instanceof Error
      ? previewQuery.error.message
      : "Preview failed.";
  }
  return "Ready";
}

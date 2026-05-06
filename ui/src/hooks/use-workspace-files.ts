import { useCallback } from "react";
import type { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listFiles, uploadFiles } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";

export function useWorkspaceFiles({
  userId,
  sessionUuid,
}: {
  userId: string;
  sessionUuid: string;
}) {
  const queryClient = useQueryClient();
  const filesQuery = useQuery({
    queryKey: queryKeys.files(userId, sessionUuid),
    queryFn: () => listFiles({ userId, sessionUuid }),
    enabled: Boolean(userId && sessionUuid),
  });
  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadFiles({ userId, sessionUuid, files }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.files(userId, sessionUuid),
      });
    },
  });
  const { refetch } = filesQuery;
  const { mutateAsync: uploadFileList } = uploadMutation;

  const refresh = useCallback(async () => {
    await refetch();
  }, [refetch]);

  const upload = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const input = event.currentTarget.elements.namedItem("files");
      if (!(input instanceof HTMLInputElement) || !input.files?.length) {
        return;
      }

      try {
        await uploadFileList(Array.from(input.files));
        input.value = "";
      } catch {
        // The status string below exposes the mutation error to the drawer.
      }
    },
    [uploadFileList],
  );

  return {
    files: filesQuery.data?.files ?? [],
    refresh,
    status: workspaceStatus(filesQuery, uploadMutation),
    upload,
  };
}

function workspaceStatus(
  filesQuery: {
    error: unknown;
    isFetching: boolean;
  },
  uploadMutation: {
    error: unknown;
    isPending: boolean;
  },
) {
  if (uploadMutation.isPending) {
    return "Uploading";
  }
  if (uploadMutation.error) {
    return messageFromError(uploadMutation.error, "Upload failed.");
  }
  if (filesQuery.isFetching) {
    return "Loading";
  }
  if (filesQuery.error) {
    return messageFromError(filesQuery.error, "File list failed.");
  }
  return "Ready";
}

function messageFromError(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

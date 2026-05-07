import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { FsListItem } from "@/lib/api";
import {
  deleteFsPath,
  listFiles,
  moveFsPath,
  renameFsPath,
  uploadFiles,
} from "@/lib/api";
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
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.files(userId, sessionUuid),
        }),
        queryClient.invalidateQueries({
          queryKey: ["file-search", userId, sessionUuid],
        }),
      ]);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (file: FsListItem) =>
      deleteFsPath({ userId, sessionUuid, path: file.path }),
    onSuccess: () => invalidateWorkspaceFiles(queryClient, userId, sessionUuid),
  });
  const moveMutation = useMutation({
    mutationFn: ({ file, destinationPath }: { file: FsListItem; destinationPath: string }) =>
      moveFsPath({
        userId,
        sessionUuid,
        path: file.path,
        destinationPath,
      }),
    onSuccess: () => invalidateWorkspaceFiles(queryClient, userId, sessionUuid),
  });
  const renameMutation = useMutation({
    mutationFn: ({ file, name }: { file: FsListItem; name: string }) =>
      renameFsPath({
        userId,
        sessionUuid,
        path: file.path,
        name,
      }),
    onSuccess: () => invalidateWorkspaceFiles(queryClient, userId, sessionUuid),
  });
  const { refetch } = filesQuery;
  const { mutateAsync: uploadFileList } = uploadMutation;
  const { mutateAsync: deleteWorkspaceFile } = deleteMutation;
  const { mutateAsync: moveWorkspacePath } = moveMutation;
  const { mutateAsync: renameWorkspacePath } = renameMutation;

  const refresh = useCallback(async () => {
    await refetch();
  }, [refetch]);

  return {
    files: filesQuery.data?.files ?? [],
    deleteFile: deleteWorkspaceFile,
    deletePendingPath: pendingPath(deleteMutation),
    movePath: moveWorkspacePath,
    operationPendingPath:
      pendingPath(deleteMutation) ??
      pendingPath(moveMutation) ??
      pendingPath(renameMutation),
    renamePath: renameWorkspacePath,
    refresh,
    status: workspaceStatus(
      filesQuery,
      uploadMutation,
      deleteMutation,
      moveMutation,
      renameMutation,
    ),
    uploadError: uploadMutation.error,
    uploadPending: uploadMutation.isPending,
    uploadSelectedFiles: uploadFileList,
  };
}

function invalidateWorkspaceFiles(
  queryClient: ReturnType<typeof useQueryClient>,
  userId: string,
  sessionUuid: string,
) {
  return Promise.all([
    queryClient.invalidateQueries({
      queryKey: ["files", userId, sessionUuid],
    }),
    queryClient.invalidateQueries({
      queryKey: ["file-search", userId, sessionUuid],
    }),
    queryClient.invalidateQueries({
      queryKey: ["file-preview", userId, sessionUuid],
    }),
  ]);
}

function pendingPath(mutation: {
  isPending: boolean;
  variables?: FsListItem | { file: FsListItem } | undefined;
}) {
  if (!mutation.isPending || !mutation.variables) {
    return null;
  }
  if ("file" in mutation.variables) {
    return mutation.variables.file.path;
  }
  return mutation.variables.path;
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
  deleteMutation: {
    error: unknown;
    isPending: boolean;
  },
  moveMutation: {
    error: unknown;
    isPending: boolean;
  },
  renameMutation: {
    error: unknown;
    isPending: boolean;
  },
) {
  if (uploadMutation.isPending) {
    return "Uploading";
  }
  if (deleteMutation.isPending) {
    return "Deleting";
  }
  if (moveMutation.isPending) {
    return "Moving";
  }
  if (renameMutation.isPending) {
    return "Renaming";
  }
  if (uploadMutation.error) {
    return messageFromError(uploadMutation.error, "Upload failed.");
  }
  if (deleteMutation.error) {
    return messageFromError(deleteMutation.error, "Delete failed.");
  }
  if (moveMutation.error) {
    return messageFromError(moveMutation.error, "Move failed.");
  }
  if (renameMutation.error) {
    return messageFromError(renameMutation.error, "Rename failed.");
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

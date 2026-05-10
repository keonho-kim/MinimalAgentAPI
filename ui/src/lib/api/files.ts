import { apiUrl } from "@/lib/backend-url";

import type {
  FsListResponse,
  FsMutationResponse,
  FsSearchResponse,
  UploadResponse,
} from "./types";

export async function listFiles({
  userId,
  sessionUuid,
  path = "/",
}: {
  userId: string;
  sessionUuid: string;
  path?: string;
}) {
  const params = new URLSearchParams({
    user_id: userId,
    uuid: sessionUuid,
    path,
  });
  const response = await fetch(apiUrl(`/api/fs/list?${params.toString()}`));

  if (!response.ok) {
    throw new Error(`File list failed: ${response.status}`);
  }

  return (await response.json()) as FsListResponse;
}

export async function searchFiles({
  userId,
  sessionUuid,
  query,
  limit = 10,
}: {
  userId: string;
  sessionUuid: string;
  query: string;
  limit?: number;
}) {
  const params = new URLSearchParams({
    user_id: userId,
    uuid: sessionUuid,
    q: query,
    limit: String(limit),
  });
  const response = await fetch(apiUrl(`/api/fs/search?${params.toString()}`));

  if (!response.ok) {
    throw new Error(`File search failed: ${response.status}`);
  }

  return (await response.json()) as FsSearchResponse;
}

export async function deleteFsPath({
  userId,
  sessionUuid,
  path,
}: {
  userId: string;
  sessionUuid: string;
  path: string;
}) {
  const params = new URLSearchParams({
    user_id: userId,
    uuid: sessionUuid,
    path,
  });
  const response = await fetch(apiUrl(`/api/fs/files?${params.toString()}`), {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(`File delete failed: ${response.status}`);
  }

  return (await response.json()) as FsMutationResponse;
}

export const deleteFile = deleteFsPath;

export async function moveFsPath({
  userId,
  sessionUuid,
  path,
  destinationPath,
}: {
  userId: string;
  sessionUuid: string;
  path: string;
  destinationPath: string;
}) {
  const response = await fetch(apiUrl("/api/fs/move"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      uuid: sessionUuid,
      path,
      destination_path: destinationPath,
    }),
  });

  if (!response.ok) {
    throw new Error(`File move failed: ${response.status}`);
  }

  return (await response.json()) as FsMutationResponse;
}

export async function renameFsPath({
  userId,
  sessionUuid,
  path,
  name,
}: {
  userId: string;
  sessionUuid: string;
  path: string;
  name: string;
}) {
  const response = await fetch(apiUrl("/api/fs/rename"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      uuid: sessionUuid,
      path,
      name,
    }),
  });

  if (!response.ok) {
    throw new Error(`File rename failed: ${response.status}`);
  }

  return (await response.json()) as FsMutationResponse;
}

export async function uploadFiles({
  userId,
  sessionUuid,
  files,
}: {
  userId: string;
  sessionUuid: string;
  files: File[];
}) {
  const form = new FormData();
  form.append("user_id", userId);
  form.append("uuid", sessionUuid);

  for (const file of files) {
    form.append("files", file);
  }

  const response = await fetch(apiUrl("/api/upload"), {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`);
  }

  return (await response.json()) as UploadResponse;
}

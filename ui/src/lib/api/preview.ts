import { apiResourceUrl, apiUrl } from "@/lib/backend-url";

import type { FsPreviewResponse } from "./types";

export async function getFilePreview({
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
  const response = await fetch(apiUrl(`/api/fs/preview?${params.toString()}`));

  if (!response.ok) {
    throw new Error(`File preview failed: ${response.status}`);
  }

  const preview = (await response.json()) as FsPreviewResponse;
  return {
    ...preview,
    source_url: apiResourceUrl(preview.source_url),
  };
}

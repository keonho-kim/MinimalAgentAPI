import { apiResourceUrl, apiUrl } from "@/lib/backend-url";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type FsListItem = {
  name: string;
  path: string;
  type: "file" | "directory";
  size: number | null;
  modified_at: number;
};

export type FsListResponse = {
  path: string;
  files: FsListItem[];
};

export type FsMutationResponse = {
  path: string;
};

export type FsSearchResponse = {
  matches: FsListItem[];
};

export type SkillListItem = {
  name: string;
  description: string;
  path: string;
};

export type SkillSearchResponse = {
  matches: SkillListItem[];
};

export type PreviewType =
  | "pdf"
  | "office_pdf"
  | "xlsx_grid"
  | "hwpx"
  | "markdown"
  | "text"
  | "code";

export type XlsxCell = {
  address: string;
  row: number;
  column: number;
  value: string | number | boolean | null;
  formula: string | null;
  style: {
    bold?: boolean;
    italic?: boolean;
    horizontal?: string | null;
    vertical?: string | null;
    color?: string;
    background?: string;
  };
};

export type XlsxSheet = {
  id: string;
  name: string;
  visible: boolean;
  index: number;
  used_range: string;
  row_count: number;
  column_count: number;
  columns: Array<{ index: number; label: string; width: number }>;
  rows: Array<{ index: number; height: number }>;
  merged_ranges: string[];
  cells: XlsxCell[];
};

export type XlsxWorkbook = {
  sheet_count: number;
  sheets: XlsxSheet[];
};

export type FsPreviewResponse = {
  path: string;
  filename: string;
  file_type: string;
  preview_type: PreviewType;
  source_url: string | null;
  workbook: XlsxWorkbook | null;
};

export type HitlActionRequest = {
  name: string;
  args: Record<string, unknown>;
  description?: string | null;
  allowed_decisions: Array<"approve" | "edit" | "reject">;
};

export type HitlRequest = {
  stream_id: string;
  actions: HitlActionRequest[];
};

export type HitlDecision =
  | { type: "approve" }
  | {
      type: "edit";
      edited_action: {
        name: string;
        args: Record<string, unknown>;
      };
    }
  | { type: "reject"; message?: string };

export type UploadedFileResponse = {
  file_id: string;
  filename: string;
  file_type: string;
  status: "uploaded" | "converted" | "conversion_failed";
  path: string | null;
  error: string | null;
};

export type UploadResponse = {
  uploaded_files: UploadedFileResponse[];
};

export async function createChatStream({
  userId,
  sessionUuid,
  message,
  chatHistory,
}: {
  userId: string;
  sessionUuid: string;
  message: string;
  chatHistory: ChatMessage[];
}) {
  const response = await fetch(apiUrl("/chat"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      uuid: sessionUuid,
      message,
      chat_history: chatHistory,
    }),
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  const body = (await response.json()) as { stream_id: string };
  return body.stream_id;
}

export async function createSessionTitle({
  userId,
  sessionUuid,
  message,
}: {
  userId: string;
  sessionUuid: string;
  message: string;
}) {
  const response = await fetch(apiUrl("/api/session/title"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      uuid: sessionUuid,
      message,
    }),
  });

  if (!response.ok) {
    throw new Error(`Title generation failed: ${response.status}`);
  }

  return (await response.json()) as { title: string };
}

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

export async function searchSkills({
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
  const response = await fetch(apiUrl(`/api/skills/search?${params.toString()}`));

  if (!response.ok) {
    throw new Error(`Skill search failed: ${response.status}`);
  }

  return (await response.json()) as SkillSearchResponse;
}

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

export async function submitHitlDecision({
  streamId,
  decisions,
}: {
  streamId: string;
  decisions: HitlDecision[];
}) {
  const response = await fetch(apiUrl(`/chat/hitl/${streamId}`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ decisions }),
  });

  if (!response.ok) {
    throw new Error(`Approval failed: ${response.status}`);
  }

  return (await response.json()) as { stream_id: string; status: string };
}

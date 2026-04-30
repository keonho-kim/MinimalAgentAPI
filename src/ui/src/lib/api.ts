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
  const response = await fetch("/chat", {
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

export async function listFiles({
  userId,
  sessionUuid,
}: {
  userId: string;
  sessionUuid: string;
}) {
  const params = new URLSearchParams({
    user_id: userId,
    uuid: sessionUuid,
    path: "/",
  });
  const response = await fetch(`/api/fs/list?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`File list failed: ${response.status}`);
  }

  return (await response.json()) as FsListResponse;
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

  const response = await fetch("/api/upload", {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status}`);
  }

  return await response.json();
}

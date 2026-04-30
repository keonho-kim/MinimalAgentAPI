export async function createChatStream({ userId, sessionUuid, message, chatHistory }) {
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

  const { stream_id: streamId } = await response.json();
  return streamId;
}

export async function listFiles({ userId, sessionUuid }) {
  const params = new URLSearchParams({
    user_id: userId,
    uuid: sessionUuid,
    path: "/",
  });
  const response = await fetch(`/api/fs/list?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`File list failed: ${response.status}`);
  }

  return await response.json();
}

export async function uploadFiles({ userId, sessionUuid, files }) {
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

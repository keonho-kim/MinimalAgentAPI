import { apiUrl } from "@/lib/backend-url";

import type { ChatMessage } from "./types";

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

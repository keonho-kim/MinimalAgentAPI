import { apiUrl } from "@/lib/backend-url";

import type { HitlDecision } from "./types";

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

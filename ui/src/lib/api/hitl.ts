import { apiUrl } from "@/lib/backend-url";

import type { HitlApprovalScope, HitlDecision } from "./types";

export async function submitHitlDecision({
  streamId,
  decisions,
  approvalScope = "once",
}: {
  streamId: string;
  decisions: HitlDecision[];
  approvalScope?: HitlApprovalScope;
}) {
  const response = await fetch(apiUrl(`/chat/hitl/${streamId}`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ decisions, approval_scope: approvalScope }),
  });

  if (!response.ok) {
    throw new Error(`Approval failed: ${response.status}`);
  }

  return (await response.json()) as { stream_id: string; status: string };
}

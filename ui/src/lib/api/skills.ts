import { apiUrl } from "@/lib/backend-url";

import type { SkillSearchResponse } from "./types";

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

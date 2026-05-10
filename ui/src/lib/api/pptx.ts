import { apiResourceUrl, apiUrl } from "@/lib/backend-url";

import type {
  PptxDeckResponse,
  PptxExportResponse,
  PptxOperation,
  PptxOperationResponse,
  PptxSearchResponse,
} from "./types";

export async function getPptxDeck({
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
  const response = await fetch(apiUrl(`/api/fs/pptx/deck?${params.toString()}`));

  if (!response.ok) {
    throw new Error(`PPTX deck load failed: ${response.status}`);
  }

  const deck = (await response.json()) as PptxDeckResponse;
  return {
    ...deck,
    source_url: apiResourceUrl(deck.source_url),
  };
}

export async function applyPptxOperations({
  userId,
  sessionUuid,
  path,
  expectedRevision,
  operations,
}: {
  userId: string;
  sessionUuid: string;
  path: string;
  expectedRevision: number;
  operations: PptxOperation[];
}) {
  const response = await fetch(apiUrl("/api/fs/pptx/operations"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      uuid: sessionUuid,
      path,
      origin: "user",
      expected_revision: expectedRevision,
      operations,
    }),
  });

  if (!response.ok) {
    throw new Error(`PPTX operation failed: ${response.status}`);
  }

  return (await response.json()) as PptxOperationResponse;
}

export async function searchPptxDeck({
  userId,
  sessionUuid,
  path,
  query,
  limit = 10,
}: {
  userId: string;
  sessionUuid: string;
  path: string;
  query: string;
  limit?: number;
}) {
  const params = new URLSearchParams({
    user_id: userId,
    uuid: sessionUuid,
    path,
    q: query,
    limit: String(limit),
  });
  const response = await fetch(apiUrl(`/api/fs/pptx/search?${params.toString()}`));

  if (!response.ok) {
    throw new Error(`PPTX search failed: ${response.status}`);
  }

  return (await response.json()) as PptxSearchResponse;
}

export async function exportPptx({
  userId,
  sessionUuid,
  path,
  format,
}: {
  userId: string;
  sessionUuid: string;
  path: string;
  format: "pdf" | "pptx";
}) {
  const response = await fetch(apiUrl(`/api/fs/pptx/export/${format}`), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: userId,
      uuid: sessionUuid,
      path,
    }),
  });

  if (!response.ok) {
    throw new Error(`PPTX export failed: ${response.status}`);
  }

  return (await response.json()) as PptxExportResponse;
}

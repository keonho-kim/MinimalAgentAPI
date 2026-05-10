import { describe, expect, test } from "bun:test";

import {
  applyPptxOperations,
  getPptxDeck,
  type PptxDeckResponse,
} from "./api";

describe("pptx api", () => {
  test("loads canonical deck metadata", async () => {
    const restore = mockFetch({
      path: "files/deck.pptx",
      filename: "deck.pptx",
      source_url: "/api/fs/preview/source?path=files%2Fdeck.pptx",
      readiness: { status: "ready", message: "Ready" },
      deck: {
        id: "deck-1",
        title: "deck",
        sourceType: "pptx",
        revision: 2,
        canvas: { width: 100, height: 100 },
        slides: [],
      },
    });

    const response = await getPptxDeck({
      userId: "user",
      sessionUuid: "session",
      path: "files/deck.pptx",
    });
    restore();

    expect(response.deck.revision).toBe(2);
    expect(response.source_url).toBe("/api/fs/preview/source?path=files%2Fdeck.pptx");
  });

  test("posts canonical operation payload", async () => {
    let capturedBody = "";
    const restore = mockFetch(
      {
        path: "files/deck.pptx",
        revision: 3,
        changed_slide_ids: ["slide-1"],
        rejected_operations: [],
        deck: {
          id: "deck-1",
          title: "deck",
          sourceType: "pptx",
          revision: 3,
          canvas: { width: 100, height: 100 },
          slides: [],
        },
      },
      (init) => {
        capturedBody = String(init?.body ?? "");
      },
    );

    await applyPptxOperations({
      userId: "user",
      sessionUuid: "session",
      path: "files/deck.pptx",
      expectedRevision: 2,
      operations: [
        {
          type: "updateText",
          slideId: "slide-1",
          elementId: "shape-2",
          content: "New title",
        },
      ],
    });
    restore();

    const payload = JSON.parse(capturedBody);
    expect(payload.expected_revision).toBe(2);
    expect(payload.operations[0].type).toBe("updateText");
    expect(payload.operations[0].elementId).toBe("shape-2");
  });
});

function mockFetch(
  payload: PptxDeckResponse | Record<string, unknown>,
  onRequest?: (init?: RequestInit) => void,
) {
  const original = globalThis.fetch;
  globalThis.fetch = ((_: RequestInfo | URL, init?: RequestInit) => {
    onRequest?.(init);
    return Promise.resolve(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  }) as typeof fetch;
  return () => {
    globalThis.fetch = original;
  };
}

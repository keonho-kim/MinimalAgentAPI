import { expect, test } from "bun:test";

import {
  apiResourceUrl,
  normalizeBackendServerUrl,
  resolveBackendUrl,
} from "../ui/src/lib/backend-url";

test("keeps API paths relative without a backend server URL", () => {
  expect(resolveBackendUrl("/chat", "")).toBe("/chat");
  expect(resolveBackendUrl("/api/fs/list?path=/", "   ")).toBe(
    "/api/fs/list?path=/",
  );
});

test("prefixes API paths with the configured backend server URL", () => {
  expect(resolveBackendUrl("/chat", "http://127.0.0.1:8000")).toBe(
    "http://127.0.0.1:8000/chat",
  );
  expect(resolveBackendUrl("api/fs/list", "http://127.0.0.1:8000/")).toBe(
    "http://127.0.0.1:8000/api/fs/list",
  );
});

test("does not rewrite absolute URLs", () => {
  expect(
    resolveBackendUrl(
      "https://files.example.com/report.pdf",
      "http://127.0.0.1:8000",
    ),
  ).toBe("https://files.example.com/report.pdf");
});

test("normalizes preview resource URLs", () => {
  expect(apiResourceUrl(null)).toBe(null);
  expect(normalizeBackendServerUrl(" http://127.0.0.1:8000/ ")).toBe(
    "http://127.0.0.1:8000",
  );
});

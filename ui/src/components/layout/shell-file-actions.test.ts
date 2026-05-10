import { describe, expect, test } from "bun:test";

import type { FsListItem } from "@/lib/api";
import { previewIsAffected } from "./shell-file-actions";

describe("shell file actions", () => {
  test("matches an active file preview by normalized path", () => {
    expect(previewIsAffected(file("/docs/report.pdf"), "docs/report.pdf/")).toBe(
      true,
    );
    expect(previewIsAffected(file("/docs/report.pdf"), "/docs/other.pdf")).toBe(
      false,
    );
  });

  test("matches previews inside an affected directory", () => {
    expect(previewIsAffected(directory("/docs"), "/docs/report.pdf")).toBe(true);
    expect(previewIsAffected(directory("/docs"), "/docs/nested/report.pdf")).toBe(
      true,
    );
    expect(previewIsAffected(directory("/docs"), "/docs-other/report.pdf")).toBe(
      false,
    );
  });
});

function file(path: string): FsListItem {
  return {
    modified_at: 0,
    name: path.split("/").at(-1) ?? path,
    path,
    size: 1,
    type: "file",
  };
}

function directory(path: string): FsListItem {
  return {
    modified_at: 0,
    name: path.split("/").at(-1) ?? path,
    path,
    size: 0,
    type: "directory",
  };
}

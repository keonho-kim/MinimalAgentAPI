import { describe, expect, test } from "bun:test";
import {
  IconFileTypePdf,
  IconFileTypePpt,
  IconFileTypeXls,
  IconFileUnknown,
  IconFolder,
  IconFolderOpen,
} from "@tabler/icons-react";

import { fileTreeIconFor } from "./file-icons";

describe("file tree icons", () => {
  test("maps PowerPoint files to the ppt icon", () => {
    expect(fileTreeIconFor({ name: "deck.pptx", type: "file" })).toBe(IconFileTypePpt);
    expect(fileTreeIconFor({ name: "legacy.PPT", type: "file" })).toBe(IconFileTypePpt);
  });

  test("maps spreadsheet and PDF files", () => {
    expect(fileTreeIconFor({ name: "budget.xlsx", type: "file" })).toBe(IconFileTypeXls);
    expect(fileTreeIconFor({ name: "report.pdf", type: "file" })).toBe(IconFileTypePdf);
  });

  test("falls back for unsupported files", () => {
    expect(fileTreeIconFor({ name: "artifact.unknown", type: "file" })).toBe(IconFileUnknown);
    expect(fileTreeIconFor({ name: "README", type: "file" })).toBe(IconFileUnknown);
  });

  test("uses folder icons based on open state", () => {
    expect(fileTreeIconFor({ name: "docs", type: "directory" })).toBe(IconFolder);
    expect(fileTreeIconFor({ name: "docs", type: "directory", isOpen: true })).toBe(IconFolderOpen);
  });
});

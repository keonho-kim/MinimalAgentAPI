import { expect, test } from "bun:test";

import {
  findActiveFileMention,
  replaceFileMention,
} from "../src/ui/src/lib/file-mentions";

test("finds the active file mention token", () => {
  expect(findActiveFileMention("read @rep", 9)).toEqual({
    start: 5,
    end: 9,
    query: "rep",
  });
});

test("rejects non-token at signs", () => {
  expect(findActiveFileMention("mail@example.com", 6)).toBeNull();
  expect(findActiveFileMention("read @rep other", 13)).toBeNull();
});

test("replaces only the active file mention token", () => {
  const token = findActiveFileMention("summarize @rep please", 14);

  expect(token).not.toBeNull();
  expect(replaceFileMention("summarize @rep please", token!, "files/report.docx"))
    .toEqual({
      value: "summarize @files/report.docx please",
      cursorIndex: 28,
    });
});

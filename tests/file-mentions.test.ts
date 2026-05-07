import { expect, test } from "bun:test";

import {
  findActiveFileMention,
  replaceFileMention,
} from "../ui/src/lib/file-mentions";

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
  expect(
    replaceFileMention("summarize @rep please", token!, {
      name: "report.docx",
      path: "files/report.docx",
      type: "file",
      size: 12,
      modified_at: 0,
    }),
  ).toEqual({
    value: "summarize report.docx please",
    cursorIndex: 21,
    mention: {
      id: expect.any(String),
      kind: "file",
      start: 10,
      end: 21,
      label: "report.docx",
      href: "/report.docx",
    },
  });
});

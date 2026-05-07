import { expect, test } from "bun:test";

import {
  normalizeMarkdownFileMentionHrefs,
  prependFileMentionAttachments,
  serializeFileMentions,
  splitLeadingFileMentionAttachments,
  splitLeadingMarkdownFileMentionAttachments,
  syncFileMentionRanges,
  validFileMentionRanges,
} from "../ui/src/lib/file-mentions";

test("serializes mixed file and skill mentions by range order", () => {
  const value = "Use writing-guide with README.md";

  expect(
    serializeFileMentions(value, [
      {
        id: "file-1",
        kind: "file",
        start: 23,
        end: 32,
        label: "README.md",
        href: "/README.md",
      },
      {
        id: "skill-1",
        kind: "skill",
        start: 4,
        end: 17,
        label: "writing-guide",
        href: "/.agents/skills/writing-guide/SKILL.md",
      },
    ]),
  ).toBe(
    "Use [writing-guide](/.agents/skills/writing-guide/SKILL.md) with [README.md](/README.md)",
  );
});

test("drops a mention token when its label is edited", () => {
  const previousValue = "Use writing-guide";
  const nextValue = "Use writing";
  const ranges = validFileMentionRanges(previousValue, [
    {
      id: "skill-1",
      kind: "skill",
      start: 4,
      end: 17,
      label: "writing-guide",
      href: "/.agents/skills/writing-guide/SKILL.md",
    },
  ]);

  expect(
    syncFileMentionRanges({
      previousValue,
      nextValue,
      ranges,
    }),
  ).toEqual([]);
});

test("prepends uploaded files before the typed message", () => {
  const message = prependFileMentionAttachments({
    value: "이 파일에 대해서 알려줘",
    ranges: [],
    attachments: [
      {
        id: "upload-1",
        label: "report.pdf",
        href: "files/report.pdf",
      },
    ],
  });

  expect(serializeFileMentions(message.value, message.ranges)).toBe(
    "[report.pdf](/report.pdf)\n이 파일에 대해서 알려줘",
  );
});

test("splits uploaded file mentions from the visible message body", () => {
  const message = prependFileMentionAttachments({
    value: "이 파일에 대해서 알려줘",
    ranges: [],
    attachments: [
      {
        id: "upload-1",
        label: "AX HUB 구축_제안요청서.pdf",
        href: "files/AX HUB 구축_제안요청서.pdf",
      },
    ],
  });

  expect(splitLeadingFileMentionAttachments(message)).toEqual({
    attachments: [
      {
        id: "upload-1",
        label: "AX HUB 구축_제안요청서.pdf",
        href: "/AX HUB 구축_제안요청서.pdf",
      },
    ],
    value: "이 파일에 대해서 알려줘",
    ranges: [],
  });
});

test("splits persisted markdown file mentions from the visible message body", () => {
  expect(
    splitLeadingMarkdownFileMentionAttachments(
      "[AX HUB 구축_제안요청서.pdf](files/AX HUB 구축_제안요청서.pdf)\n이 파일에 대해서 알려줘",
    ),
  ).toEqual({
    attachments: [
      {
        id: "markdown:0:48:files/AX HUB 구축_제안요청서.pdf",
        label: "AX HUB 구축_제안요청서.pdf",
        href: "files/AX HUB 구축_제안요청서.pdf",
      },
    ],
    value: "이 파일에 대해서 알려줘",
  });
});

test("normalizes file mention href spaces before markdown rendering", () => {
  expect(
    normalizeMarkdownFileMentionHrefs(
      "현재 파일: [AX HUB 구축_제안요청서.pdf](/AX HUB 구축_제안요청서.pdf)",
    ),
  ).toBe(
    "현재 파일: [AX HUB 구축_제안요청서.pdf](/AX%20HUB%20구축_제안요청서.pdf)",
  );
});

test("normalizes public file paths to agent workspace hrefs", () => {
  const message = prependFileMentionAttachments({
    value: "확인해줘",
    ranges: [],
    attachments: [
      {
        id: "upload-1",
        label: "report.pdf",
        href: "files/report.pdf",
      },
    ],
  });

  expect(message.ranges[0]?.href).toBe("/report.pdf");
  expect(serializeFileMentions(message.value, message.ranges)).toBe(
    "[report.pdf](/report.pdf)\n확인해줘",
  );
});

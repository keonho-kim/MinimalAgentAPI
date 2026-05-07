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
  const value = "Use $writing-guide with README.md";

  expect(
    serializeFileMentions(value, [
      {
        id: "file-1",
        kind: "file",
        start: 24,
        end: 33,
        label: "README.md",
        href: "/README.md",
      },
      {
        id: "skill-1",
        kind: "skill",
        start: 4,
        end: 18,
        label: "$writing-guide",
        href: "/.agents/skills/writing-guide/SKILL.md",
      },
    ]),
  ).toBe(
    "Use [$writing-guide](/.agents/skills/writing-guide/SKILL.md) with [README.md](/README.md)",
  );
});

test("drops a mention token when its label is edited", () => {
  const previousValue = "Use $writing-guide";
  const nextValue = "Use $writing";
  const ranges = validFileMentionRanges(previousValue, [
    {
      id: "skill-1",
      kind: "skill",
      start: 4,
      end: 18,
      label: "$writing-guide",
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

test("splits persisted markdown file mentions with parentheses in href", () => {
  expect(
    splitLeadingMarkdownFileMentionAttachments(
      "[(2022년 제2차) 경기도주식회사 정규직 직원 채용 공고문.pdf](/(2022년%20제2차)%20경기도주식회사%20정규직%20직원%20채용%20공고문.pdf)\n요약해줘",
    ),
  ).toEqual({
    attachments: [
      {
        id: expect.any(String),
        label: "(2022년 제2차) 경기도주식회사 정규직 직원 채용 공고문.pdf",
        href: "/(2022년%20제2차)%20경기도주식회사%20정규직%20직원%20채용%20공고문.pdf",
      },
    ],
    value: "요약해줘",
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

test("normalizes file mention href with balanced parentheses", () => {
  expect(
    normalizeMarkdownFileMentionHrefs(
      "현재 파일: [(2022년 제2차) 경기도주식회사 정규직 직원 채용 공고문.pdf](/(2022년%20제2차)%20경기도주식회사%20정규직%20직원%20채용%20공고문.pdf)",
    ),
  ).toBe(
    "현재 파일: [(2022년 제2차) 경기도주식회사 정규직 직원 채용 공고문.pdf](/(2022년%20제2차)%20경기도주식회사%20정규직%20직원%20채용%20공고문.pdf)",
  );
});

test("serializes selected hwpx file mentions with Korean text and parentheses", () => {
  const value = "붙임3. 공동연구 제안요청서(RFP).hwpx 내용을 확인해줘";

  expect(
    normalizeMarkdownFileMentionHrefs(
      serializeFileMentions(value, [
        {
          id: "file-1",
          kind: "file",
          start: 0,
          end: 25,
          label: "붙임3. 공동연구 제안요청서(RFP).hwpx",
          href: "/붙임3. 공동연구 제안요청서(RFP).hwpx",
        },
      ]),
    ),
  ).toBe(
    "[붙임3. 공동연구 제안요청서(RFP).hwpx](/붙임3.%20공동연구%20제안요청서(RFP).hwpx) 내용을 확인해줘",
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

import { expect, test } from "bun:test";

import {
  findActiveFileMention,
  findActiveSkillMention,
  insertFileMentionAttachments,
  replaceFileMention,
  replaceSkillMention,
} from "../ui/src/lib/file-mentions";

test("finds the active file mention token", () => {
  expect(findActiveFileMention("read @rep", 9)).toEqual({
    start: 5,
    end: 9,
    query: "rep",
  });
  expect(findActiveFileMention("@", 1)).toEqual({
    start: 0,
    end: 1,
    query: "",
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

test("replaces a Korean hwpx file mention token", () => {
  const token = findActiveFileMention("@", 1);

  expect(token).not.toBeNull();
  expect(
    replaceFileMention("@", token!, {
      name: "붙임3. 공동연구 제안요청서(RFP).hwpx",
      path: "files/붙임3. 공동연구 제안요청서(RFP).hwpx",
      type: "file",
      size: 12,
      modified_at: 0,
    }),
  ).toEqual({
    value: "붙임3. 공동연구 제안요청서(RFP).hwpx",
    cursorIndex: 25,
    mention: {
      id: expect.any(String),
      kind: "file",
      start: 0,
      end: 25,
      label: "붙임3. 공동연구 제안요청서(RFP).hwpx",
      href: "/붙임3. 공동연구 제안요청서(RFP).hwpx",
    },
  });
});

test("inserts uploaded file mentions at the cursor", () => {
  expect(
    insertFileMentionAttachments({
      value: "요약해줘",
      ranges: [],
      cursorIndex: 0,
      attachments: [
        {
          id: "upload-1",
          label: "(2022년 제2차) 경기도주식회사 정규직 직원 채용 공고문.pdf",
          href: "files/(2022년 제2차) 경기도주식회사 정규직 직원 채용 공고문.pdf",
        },
      ],
    }),
  ).toEqual({
    value: "(2022년 제2차) 경기도주식회사 정규직 직원 채용 공고문.pdf 요약해줘",
    cursorIndex: 38,
    ranges: [
      {
        id: "upload-1",
        kind: "file",
        start: 0,
        end: 37,
        label: "(2022년 제2차) 경기도주식회사 정규직 직원 채용 공고문.pdf",
        href: "/(2022년 제2차) 경기도주식회사 정규직 직원 채용 공고문.pdf",
      },
    ],
  });
});

test("replaces active skill mention token with dollar-prefixed label", () => {
  const token = findActiveSkillMention("use $wri", 8);

  expect(token).not.toBeNull();
  expect(
    replaceSkillMention("use $wri", token!, {
      name: "writing-guide",
      description: "Writing guidance",
      path: "/.agents/skills/writing-guide/SKILL.md",
    }),
  ).toEqual({
    value: "use $writing-guide",
    cursorIndex: 18,
    mention: {
      id: expect.any(String),
      kind: "skill",
      start: 4,
      end: 18,
      label: "$writing-guide",
      href: "/.agents/skills/writing-guide/SKILL.md",
    },
  });
});

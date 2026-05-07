import { describe, expect, test } from "bun:test";

import {
  composerDocFromText,
  composerPayloadFromJson,
  composerPayloadFromText,
  FILE_MENTION_NODE,
  SKILL_MENTION_NODE,
} from "./composer-editor";
import {
  fileMentionAttachmentFromDragPayload,
  markdownFileMention,
} from "./file-mentions";

describe("composer editor serialization", () => {
  test("serializes text with file and skill mentions", () => {
    const payload = composerPayloadFromJson({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [
            { type: "text", text: "Read " },
            {
              type: FILE_MENTION_NODE,
              attrs: { id: "files/report.pdf", label: "report.pdf" },
            },
            { type: "text", text: " with " },
            {
              type: SKILL_MENTION_NODE,
              attrs: { id: "/.agents/skills/doc", label: "$doc" },
            },
          ],
        },
      ],
    });

    expect(payload.displayContent).toBe("Read report.pdf with $doc");
    expect(payload.serializedContent).toBe(
      "Read [report.pdf](files/report.pdf) with [$doc](/.agents/skills/doc)",
    );
    expect(payload.fileMentions).toHaveLength(2);
    expect(payload.fileMentions[0].kind).toBe("file");
    expect(payload.fileMentions[1].kind).toBe("skill");
  });

  test("preserves paragraphs and hard breaks", () => {
    const payload = composerPayloadFromJson({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [
            { type: "text", text: "first" },
            { type: "hardBreak" },
            { type: "text", text: "line" },
          ],
        },
        {
          type: "paragraph",
          content: [{ type: "text", text: "second" }],
        },
      ],
    });

    expect(payload.displayContent).toBe("first\nline\nsecond");
    expect(payload.serializedContent).toBe("first\nline\nsecond");
    expect(payload.fileMentions).toHaveLength(0);
  });

  test("creates a fallback payload from plain text", () => {
    const payload = composerPayloadFromText("hello\nworld");

    expect(payload.displayContent).toBe("hello\nworld");
    expect(payload.serializedContent).toBe("hello\nworld");
    expect(payload.fileMentions).toHaveLength(0);
  });

  test("creates a Tiptap document from fallback text", () => {
    expect(JSON.stringify(composerDocFromText("hello\nworld"))).toBe(JSON.stringify({
      type: "doc",
      content: [
        { type: "paragraph", content: [{ type: "text", text: "hello" }] },
        { type: "paragraph", content: [{ type: "text", text: "world" }] },
      ],
    }));
  });

  test("serializes drawer drag file payloads as markdown mentions", () => {
    const attachment = fileMentionAttachmentFromDragPayload({
      name: "report.pdf",
      path: "/workspace/files/reports/report.pdf",
    });

    expect(attachment.label).toBe("report.pdf");
    expect(attachment.href).toBe("/reports/report.pdf");
    expect(markdownFileMention(attachment)).toBe(
      "[report.pdf](/reports/report.pdf)",
    );
  });
});

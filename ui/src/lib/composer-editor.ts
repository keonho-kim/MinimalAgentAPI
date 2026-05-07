import type { FileMentionAttachment, FileMentionRange } from "@/lib/file-mentions";
import { serializeFileMentions, validFileMentionRanges } from "@/lib/file-mentions";

export const FILE_MENTION_NODE = "fileMention";
export const SKILL_MENTION_NODE = "skillMention";

export type ComposerSubmitPayload = {
  displayContent: string;
  serializedContent: string;
  fileMentions: FileMentionRange[];
};

export type ComposerMentionItem = {
  id: string;
  label: string;
  href: string;
};

export type ComposerEditorHandle = {
  insertFileMentions(attachments: FileMentionAttachment[]): void;
  clear(): void;
  focus(): void;
};

export type ComposerEditorRuntimeHandle = ComposerEditorHandle & {
  getPayload(): ComposerSubmitPayload;
  isEmpty(): boolean;
};

export type TiptapJsonNode = {
  type?: string;
  text?: string;
  attrs?: {
    id?: string | null;
    label?: string | null;
  };
  content?: TiptapJsonNode[];
};

export function composerPayloadFromText(value: string): ComposerSubmitPayload {
  return {
    displayContent: value,
    fileMentions: [],
    serializedContent: value,
  };
}

export function composerDocFromText(value: string): TiptapJsonNode {
  const lines = value.split("\n");
  return {
    type: "doc",
    content: lines.map((line) => ({
      type: "paragraph",
      content: line ? [{ type: "text", text: line }] : undefined,
    })),
  };
}

export function composerPayloadFromJson(doc: TiptapJsonNode): ComposerSubmitPayload {
  let displayContent = "";
  const fileMentions: FileMentionRange[] = [];

  function appendText(text: string) {
    displayContent += text;
  }

  function appendMention(node: TiptapJsonNode) {
    const label = node.attrs?.label?.trim();
    const href = node.attrs?.id?.trim();
    if (!label || !href) {
      return;
    }

    const start = displayContent.length;
    appendText(label);
    fileMentions.push({
      id: `${node.type}:${href}:${start}`,
      kind: node.type === SKILL_MENTION_NODE ? "skill" : "file",
      start,
      end: displayContent.length,
      label,
      href,
    });
  }

  function visit(node: TiptapJsonNode) {
    if (node.type === "text") {
      appendText(node.text ?? "");
      return;
    }
    if (node.type === "hardBreak") {
      appendText("\n");
      return;
    }
    if (node.type === FILE_MENTION_NODE || node.type === SKILL_MENTION_NODE) {
      appendMention(node);
      return;
    }

    const children = node.content ?? [];
    for (const child of children) {
      visit(child);
    }
  }

  const blocks = doc.content ?? [];
  blocks.forEach((block, index) => {
    if (index > 0) {
      appendText("\n");
    }
    visit(block);
  });

  const validMentions = validFileMentionRanges(displayContent, fileMentions);
  return {
    displayContent,
    fileMentions: validMentions,
    serializedContent: serializeFileMentions(displayContent, validMentions),
  };
}

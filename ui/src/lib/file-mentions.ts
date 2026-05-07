export type MentionKind = "file" | "skill";

export type FileMentionRange = {
  kind: MentionKind;
  id: string;
  start: number;
  end: number;
  label: string;
  href: string;
};

export type MarkdownFileMention = {
  start: number;
  end: number;
  label: string;
  href: string;
};

export type FileMentionAttachment = {
  id: string;
  label: string;
  href: string;
};

export const FILE_MENTION_DRAG_MIME = "application/x-minimal-agent-file";

export type FileMentionDragPayload = {
  name: string;
  path: string;
};

export function fileMentionAttachmentFromDragPayload(
  payload: FileMentionDragPayload,
): FileMentionAttachment {
  return {
    id: `drag:${payload.path}`,
    label: payload.name,
    href: toAgentFileHref(payload.path),
  };
}

export function markdownFileMention(value: FileMentionAttachment) {
  return `[${escapeMarkdownLabel(displayFileMentionLabel(value.label))}](${toAgentFileHref(
    value.href,
  )})`;
}

export function readFileMentionDragPayload(
  dataTransfer: DataTransfer,
): FileMentionDragPayload | null {
  const raw = dataTransfer.getData(FILE_MENTION_DRAG_MIME);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<FileMentionDragPayload>;
    if (!parsed.name?.trim() || !parsed.path?.trim()) {
      return null;
    }
    return {
      name: parsed.name,
      path: parsed.path,
    };
  } catch {
    return null;
  }
}

export function writeFileMentionDragPayload(
  dataTransfer: DataTransfer,
  payload: FileMentionDragPayload,
  options: { effectAllowed?: DataTransfer["effectAllowed"] } = {},
) {
  const attachment = fileMentionAttachmentFromDragPayload(payload);
  dataTransfer.effectAllowed = options.effectAllowed ?? "copy";
  dataTransfer.setData(FILE_MENTION_DRAG_MIME, JSON.stringify(payload));
  dataTransfer.setData("text/plain", markdownFileMention(attachment));
}

export function serializeFileMentions(value: string, ranges: FileMentionRange[]) {
  const validRanges = validFileMentionRanges(value, ranges);
  let cursor = 0;
  let output = "";

  for (const range of validRanges) {
    output += value.slice(cursor, range.start);
    output += `[${escapeMarkdownLabel(range.label)}](${range.href})`;
    cursor = range.end;
  }

  return `${output}${value.slice(cursor)}`;
}

export function splitLeadingFileMentionAttachments({
  value,
  ranges,
}: {
  value: string;
  ranges: FileMentionRange[];
}) {
  const validRanges = validFileMentionRanges(value, ranges);
  const attachments: FileMentionAttachment[] = [];
  let cursor = 0;
  let rangeIndex = 0;

  for (; rangeIndex < validRanges.length; rangeIndex += 1) {
    const range = validRanges[rangeIndex];
    const gap = value.slice(cursor, range.start);
    if (range.kind !== "file" || gap.trim()) {
      break;
    }

    attachments.push({
      id: range.id,
      label: range.label,
      href: range.href,
    });
    cursor = range.end;
  }

  if (!attachments.length) {
    return {
      attachments,
      value,
      ranges: validRanges,
    };
  }

  const bodyStart = cursor + (value.slice(cursor).match(/^\s*/)?.[0].length ?? 0);
  const bodyValue = value.slice(bodyStart);
  const bodyRanges = validRanges
    .slice(rangeIndex)
    .filter((range) => range.start >= bodyStart)
    .map((range) => ({
      ...range,
      start: range.start - bodyStart,
      end: range.end - bodyStart,
    }));

  return {
    attachments,
    value: bodyValue,
    ranges: validFileMentionRanges(bodyValue, bodyRanges),
  };
}

export function splitLeadingMarkdownFileMentionAttachments(value: string) {
  const mentions = parseMarkdownFileMentions(value);
  const attachments: FileMentionAttachment[] = [];
  let cursor = 0;
  let mentionIndex = 0;

  for (; mentionIndex < mentions.length; mentionIndex += 1) {
    const mention = mentions[mentionIndex];
    const gap = value.slice(cursor, mention.start);
    if (gap.trim()) {
      break;
    }

    attachments.push({
      id: `markdown:${mention.start}:${mention.end}:${mention.href}`,
      label: mention.label,
      href: mention.href,
    });
    cursor = mention.end;
  }

  if (!attachments.length) {
    return {
      attachments,
      value,
    };
  }

  const bodyStart = cursor + (value.slice(cursor).match(/^\s*/)?.[0].length ?? 0);

  return {
    attachments,
    value: value.slice(bodyStart),
  };
}

export function validFileMentionRanges(
  value: string,
  ranges: FileMentionRange[],
) {
  const sortedRanges = [...ranges].sort((left, right) => left.start - right.start);
  const validRanges: FileMentionRange[] = [];
  let cursor = 0;

  for (const range of sortedRanges) {
    if (
      range.start < cursor ||
      range.start < 0 ||
      range.end > value.length ||
      range.start >= range.end ||
      value.slice(range.start, range.end) !== range.label
    ) {
      continue;
    }

    validRanges.push(range);
    cursor = range.end;
  }

  return validRanges;
}

export function parseMarkdownFileMentions(value: string): MarkdownFileMention[] {
  const mentions: MarkdownFileMention[] = [];
  let index = 0;

  while (index < value.length) {
    const start = value.indexOf("[", index);
    if (start === -1) {
      break;
    }
    if (value[start - 1] === "!") {
      index = start + 1;
      continue;
    }

    const labelEnd = findUnescaped(value, "]", start + 1);
    if (labelEnd === -1 || value[labelEnd + 1] !== "(") {
      index = start + 1;
      continue;
    }

    const hrefStart = labelEnd + 2;
    const hrefEnd = findMarkdownHrefEnd(value, hrefStart);
    if (hrefEnd === -1) {
      index = start + 1;
      continue;
    }

    const label = unescapeMarkdownLabel(value.slice(start + 1, labelEnd)).trim();
    const href = value.slice(hrefStart, hrefEnd).trim();
    if (label && href && isFileMentionHref(href)) {
      mentions.push({
        start,
        end: hrefEnd + 1,
        label,
        href,
      });
    }
    index = hrefEnd + 1;
  }

  return mentions;
}

export function normalizeMarkdownFileMentionHrefs(value: string) {
  const mentions = parseMarkdownFileMentions(value);
  if (!mentions.length) {
    return value;
  }

  let cursor = 0;
  let output = "";
  for (const mention of mentions) {
    output += value.slice(cursor, mention.start);
    output += `[${escapeMarkdownLabel(displayFileMentionLabel(mention.label))}](${mention.href.replaceAll(
      " ",
      "%20",
    )})`;
    cursor = mention.end;
  }

  return `${output}${value.slice(cursor)}`;
}

export function isFileMentionHref(href: string) {
  return !isSkillMentionHref(href) && !/^(https?:|mailto:)/i.test(href);
}

export function isSkillMentionHref(href: string) {
  return href.startsWith("/.agents/skills/");
}

export function toAgentFileHref(path: string) {
  const normalized = path.trim().replaceAll("\\", "/");
  if (!normalized || isSkillMentionHref(normalized)) {
    return normalized;
  }

  for (const prefix of [
    "/workspace/files/",
    "workspace/files/",
    "/files/",
    "files/",
  ]) {
    if (normalized.startsWith(prefix)) {
      return `/${normalized.slice(prefix.length)}`;
    }
  }

  if (
    normalized === "/workspace" ||
    normalized === "workspace" ||
    normalized === "/workspace/files" ||
    normalized === "workspace/files" ||
    normalized === "/files" ||
    normalized === "files"
  ) {
    return "/";
  }

  return normalized.startsWith("/") ? normalized : `/${normalized}`;
}

export function displayFileMentionLabel(label: string) {
  return label.trim().replace(/^\/+/, "");
}

function escapeMarkdownLabel(value: string) {
  return value.replaceAll("\\", "\\\\").replaceAll("[", "\\[").replaceAll("]", "\\]");
}

function unescapeMarkdownLabel(value: string) {
  return value.replace(/\\([\\[\]])/g, "$1");
}

function findUnescaped(value: string, target: string, start: number) {
  for (let index = start; index < value.length; index += 1) {
    if (value[index] !== target) {
      continue;
    }

    if (!isEscaped(value, index)) {
      return index;
    }
  }

  return -1;
}

function findMarkdownHrefEnd(value: string, start: number) {
  let parenDepth = 0;

  for (let index = start; index < value.length; index += 1) {
    const char = value[index];
    if (isEscaped(value, index)) {
      continue;
    }

    if (char === "(") {
      parenDepth += 1;
      continue;
    }

    if (char === ")") {
      if (parenDepth > 0) {
        parenDepth -= 1;
        continue;
      }
      return index;
    }
  }

  return -1;
}

function isEscaped(value: string, index: number) {
  let slashCount = 0;
  for (
    let previous = index - 1;
    previous >= 0 && value[previous] === "\\";
    previous -= 1
  ) {
    slashCount += 1;
  }
  return slashCount % 2 === 1;
}

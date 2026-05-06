import type { FsListItem, SkillListItem } from "@/lib/api";
import { createId } from "@/lib/id";

export type MentionKind = "file" | "skill";

export type FileMentionSearchToken = {
  start: number;
  end: number;
  query: string;
};

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

export function findActiveFileMention(
  value: string,
  cursorIndex: number,
): FileMentionSearchToken | null {
  return findActiveMention(value, cursorIndex, "@");
}

export function findActiveSkillMention(
  value: string,
  cursorIndex: number,
): FileMentionSearchToken | null {
  return findActiveMention(value, cursorIndex, "$");
}

function findActiveMention(
  value: string,
  cursorIndex: number,
  trigger: "@" | "$",
): FileMentionSearchToken | null {
  if (cursorIndex < 0 || cursorIndex > value.length) {
    return null;
  }

  const atIndex = value.lastIndexOf(trigger, Math.max(cursorIndex - 1, 0));
  if (atIndex === -1) {
    return null;
  }

  const prefix = value[atIndex - 1];
  if (prefix && !/\s/.test(prefix)) {
    return null;
  }

  const beforeCursor = value.slice(atIndex + 1, cursorIndex);
  if (/[\s@$]/.test(beforeCursor)) {
    return null;
  }

  const afterCursor = value.slice(cursorIndex);
  const tokenTail = afterCursor.match(/^[^\s@$]*/)?.[0] ?? "";
  const end = cursorIndex + tokenTail.length;
  const query = value.slice(atIndex + 1, end);

  return {
    start: atIndex,
    end,
    query,
  };
}

export function replaceFileMention(
  value: string,
  token: FileMentionSearchToken,
  file: FsListItem,
) {
  const mention = file.name;
  const nextValue = `${value.slice(0, token.start)}${mention}${value.slice(
    token.end,
  )}`;
  const mentionStart = token.start;
  const mentionEnd = mentionStart + mention.length;

  return {
    value: nextValue,
    cursorIndex: mentionEnd,
    mention: {
      id: createId(),
      kind: "file",
      start: mentionStart,
      end: mentionEnd,
      label: file.name,
      href: file.path,
    } satisfies FileMentionRange,
  };
}

export function replaceSkillMention(
  value: string,
  token: FileMentionSearchToken,
  skill: SkillListItem,
) {
  const mention = skill.name;
  const nextValue = `${value.slice(0, token.start)}${mention}${value.slice(
    token.end,
  )}`;
  const mentionStart = token.start;
  const mentionEnd = mentionStart + mention.length;

  return {
    value: nextValue,
    cursorIndex: mentionEnd,
    mention: {
      id: createId(),
      kind: "skill",
      start: mentionStart,
      end: mentionEnd,
      label: skill.name,
      href: skill.path,
    } satisfies FileMentionRange,
  };
}

export function syncFileMentionRanges({
  previousValue,
  nextValue,
  ranges,
}: {
  previousValue: string;
  nextValue: string;
  ranges: FileMentionRange[];
}) {
  const prefixLength = commonPrefixLength(previousValue, nextValue);
  const suffixLength = commonSuffixLength(previousValue, nextValue, prefixLength);
  const previousChangedEnd = previousValue.length - suffixLength;
  const delta = nextValue.length - previousValue.length;
  const nextRanges: FileMentionRange[] = [];

  for (const range of ranges) {
    if (range.end <= prefixLength) {
      nextRanges.push(range);
      continue;
    }

    if (range.start >= previousChangedEnd) {
      nextRanges.push({
        ...range,
        start: range.start + delta,
        end: range.end + delta,
      });
    }
  }

  return validFileMentionRanges(nextValue, nextRanges);
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

export function trimFileMentionText(value: string, ranges: FileMentionRange[]) {
  const start = value.search(/\S/);
  if (start === -1) {
    return { value: "", ranges: [] };
  }

  const end = value.trimEnd().length;
  const nextValue = value.slice(start, end);
  const nextRanges = ranges
    .filter((range) => range.start >= start && range.end <= end)
    .map((range) => ({
      ...range,
      start: range.start - start,
      end: range.end - start,
    }));

  return {
    value: nextValue,
    ranges: validFileMentionRanges(nextValue, nextRanges),
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
    const hrefEnd = findUnescaped(value, ")", hrefStart);
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

export function isFileMentionHref(href: string) {
  return !isSkillMentionHref(href) && !/^(https?:|mailto:)/i.test(href);
}

export function isSkillMentionHref(href: string) {
  return href.startsWith("/.agents/skills/");
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

    let slashCount = 0;
    for (let previous = index - 1; previous >= 0 && value[previous] === "\\"; previous -= 1) {
      slashCount += 1;
    }
    if (slashCount % 2 === 0) {
      return index;
    }
  }

  return -1;
}

function commonPrefixLength(left: string, right: string) {
  const length = Math.min(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    if (left[index] !== right[index]) {
      return index;
    }
  }
  return length;
}

function commonSuffixLength(left: string, right: string, prefixLength: number) {
  let suffixLength = 0;
  const maxLength = Math.min(left.length, right.length) - prefixLength;

  while (
    suffixLength < maxLength &&
    left[left.length - suffixLength - 1] === right[right.length - suffixLength - 1]
  ) {
    suffixLength += 1;
  }

  return suffixLength;
}

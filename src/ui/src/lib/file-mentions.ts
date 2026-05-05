export type FileMentionToken = {
  start: number;
  end: number;
  query: string;
};

export function findActiveFileMention(
  value: string,
  cursorIndex: number,
): FileMentionToken | null {
  if (cursorIndex < 0 || cursorIndex > value.length) {
    return null;
  }

  const atIndex = value.lastIndexOf("@", Math.max(cursorIndex - 1, 0));
  if (atIndex === -1) {
    return null;
  }

  const prefix = value[atIndex - 1];
  if (prefix && !/\s/.test(prefix)) {
    return null;
  }

  const beforeCursor = value.slice(atIndex + 1, cursorIndex);
  if (beforeCursor.includes("@") || /\s/.test(beforeCursor)) {
    return null;
  }

  const afterCursor = value.slice(cursorIndex);
  const tokenTail = afterCursor.match(/^[^\s@]*/)?.[0] ?? "";
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
  token: FileMentionToken,
  path: string,
) {
  const mention = `@${path}`;
  const nextValue = `${value.slice(0, token.start)}${mention}${value.slice(
    token.end,
  )}`;

  return {
    value: nextValue,
    cursorIndex: token.start + mention.length,
  };
}

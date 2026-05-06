import { useCallback, useEffect, useMemo, useState } from "react";
import type { KeyboardEvent, RefObject } from "react";
import { useQuery } from "@tanstack/react-query";

import type { FsListItem } from "@/lib/api";
import { searchFiles } from "@/lib/api";
import {
  type FileMentionRange,
  findActiveFileMention,
  replaceFileMention,
} from "@/lib/file-mentions";
import { queryKeys } from "@/lib/query-keys";

export type MentionStatus = "idle" | "loading" | "ready" | "error";

export function useFileMentions({
  userId,
  sessionUuid,
  message,
  insertFileMention,
  textareaRef,
}: {
  userId: string;
  sessionUuid: string;
  message: string;
  insertFileMention(value: string, range: FileMentionRange): void;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
}) {
  const [cursorIndex, setCursorIndex] = useState(0);
  const [activeIndex, setActiveIndex] = useState(0);
  const [closedKey, setClosedKey] = useState("");
  const activeMention = useMemo(
    () => findActiveFileMention(message, cursorIndex),
    [message, cursorIndex],
  );
  const query = activeMention?.query.trim() ?? "";
  const canSearch = query.length > 0 && !query.includes("/");
  const mentionKey = `${sessionUuid}:${query}`;
  const panelEnabled = Boolean(activeMention && canSearch && closedKey !== mentionKey);
  const searchQuery = useQuery({
    queryKey: queryKeys.fileSearch(userId, sessionUuid, query, 10),
    queryFn: () =>
      searchFiles({
        userId,
        sessionUuid,
        query,
        limit: 10,
      }),
    enabled: panelEnabled,
  });
  const matches = searchQuery.data?.matches ?? [];
  const status = mentionStatus(panelEnabled, searchQuery);

  useEffect(() => {
    setActiveIndex(0);
  }, [mentionKey]);

  const close = useCallback(() => {
    setClosedKey(mentionKey);
    setActiveIndex(0);
  }, [mentionKey]);

  const syncCursor = useCallback((element: HTMLTextAreaElement) => {
    setCursorIndex(element.selectionStart);
  }, []);

  const select = useCallback(
    (file: FsListItem) => {
      if (!activeMention) {
        return;
      }

      const next = replaceFileMention(message, activeMention, file);
      insertFileMention(next.value, next.mention);
      setClosedKey(mentionKey);
      setActiveIndex(0);

      requestAnimationFrame(() => {
        textareaRef.current?.focus();
        textareaRef.current?.setSelectionRange(next.cursorIndex, next.cursorIndex);
        setCursorIndex(next.cursorIndex);
      });
    },
    [activeMention, insertFileMention, mentionKey, message, textareaRef],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (!activeMention || !canSearch || status === "idle") {
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }

      if (matches.length === 0) {
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveIndex((current) => (current + 1) % matches.length);
        return;
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveIndex((current) => (current - 1 + matches.length) % matches.length);
        return;
      }

      if (event.key === "Enter" || event.key === "Tab") {
        event.preventDefault();
        select(matches[activeIndex]);
      }
    },
    [
      activeIndex,
      activeMention,
      canSearch,
      close,
      matches,
      select,
      status,
    ],
  );

  return {
    active: panelEnabled && status !== "idle",
    activeIndex,
    close,
    cursorIndex,
    handleKeyDown,
    matches,
    select,
    status,
    syncCursor,
  };
}

function mentionStatus(
  panelEnabled: boolean,
  searchQuery: {
    error: unknown;
    isFetching: boolean;
  },
): MentionStatus {
  if (!panelEnabled) {
    return "idle";
  }
  if (searchQuery.isFetching) {
    return "loading";
  }
  if (searchQuery.error) {
    return "error";
  }
  return "ready";
}

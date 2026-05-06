import { useCallback, useEffect, useMemo, useState } from "react";
import type { KeyboardEvent, RefObject } from "react";
import { useQuery } from "@tanstack/react-query";

import type { SkillListItem } from "@/lib/api";
import { searchSkills } from "@/lib/api";
import {
  type FileMentionRange,
  findActiveSkillMention,
  replaceSkillMention,
} from "@/lib/file-mentions";
import { queryKeys } from "@/lib/query-keys";
import type { MentionStatus } from "@/hooks/use-file-mentions";

export function useSkillMentions({
  userId,
  sessionUuid,
  message,
  insertMentionRange,
  textareaRef,
}: {
  userId: string;
  sessionUuid: string;
  message: string;
  insertMentionRange(value: string, range: FileMentionRange): void;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
}) {
  const [cursorIndex, setCursorIndex] = useState(0);
  const [activeIndex, setActiveIndex] = useState(0);
  const [closedKey, setClosedKey] = useState("");
  const activeMention = useMemo(
    () => findActiveSkillMention(message, cursorIndex),
    [message, cursorIndex],
  );
  const query = activeMention?.query.trim() ?? "";
  const mentionKey = `${sessionUuid}:${query}`;
  const panelEnabled = Boolean(activeMention && closedKey !== mentionKey);
  const searchQuery = useQuery({
    queryKey: queryKeys.skillSearch(userId, sessionUuid, query, 10),
    queryFn: () =>
      searchSkills({
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
    (skill: SkillListItem) => {
      if (!activeMention) {
        return;
      }

      const next = replaceSkillMention(message, activeMention, skill);
      insertMentionRange(next.value, next.mention);
      setClosedKey(mentionKey);
      setActiveIndex(0);

      requestAnimationFrame(() => {
        textareaRef.current?.focus();
        textareaRef.current?.setSelectionRange(next.cursorIndex, next.cursorIndex);
        setCursorIndex(next.cursorIndex);
      });
    },
    [activeMention, insertMentionRange, mentionKey, message, textareaRef],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (!activeMention || status === "idle") {
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
    [activeIndex, activeMention, close, matches, select, status],
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

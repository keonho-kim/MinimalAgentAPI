import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";

import type { ChatMessage, HitlRequest } from "@/lib/api";
import { createChatStream, createSessionTitle } from "@/lib/api";
import {
  appendAgentUiEvent,
  errorMessage as createErrorMessage,
  hydrateSessionMessages,
  userMessage,
} from "@/lib/chat-messages";
import type { UiMessage } from "@/lib/chat-messages";
import {
  serializeFileMentions,
  syncFileMentionRanges,
  trimFileMentionText,
  validFileMentionRanges,
} from "@/lib/file-mentions";
import type { FileMentionRange } from "@/lib/file-mentions";
import {
  buildSessionTitleContext,
  firstCompletedExchangeTitleContext,
  userMessageCount,
} from "@/lib/session-title";
import { openChatEventSource } from "@/lib/stream";
import {
  DEFAULT_SESSION_TITLE,
  getSessionHistory,
  saveSessionHistory,
} from "@/store/session-store";

export function useChatStream({
  userId,
  sessionUuid,
  currentSessionTitle,
  renameSession,
  touchSession,
  onBeforeSubmit,
  onHitlRequest,
  onHitlResumed,
  onStreamCreated,
  onStreamCleared,
}: {
  userId: string;
  sessionUuid: string;
  currentSessionTitle: string | undefined;
  renameSession(uuid: string, title: string): void;
  touchSession(uuid: string): void;
  onBeforeSubmit(): void;
  onHitlRequest(request: HitlRequest): void;
  onHitlResumed(): void;
  onStreamCreated(streamId: string): void;
  onStreamCleared(): void;
}) {
  const [message, setMessage] = useState("");
  const [mentionRanges, setMentionRanges] = useState<FileMentionRange[]>([]);
  const [status, setStatus] = useState("Idle");
  const [uiMessages, setUiMessages] = useState<UiMessage[]>(() =>
    hydrateSessionMessages(userId, sessionUuid),
  );
  const messageRef = useRef(message);
  const titleRequestKeysRef = useRef(new Set<string>());
  const eventSourceRef = useRef<EventSource | null>(null);
  const streamMutation = useMutation({
    mutationFn: createChatStream,
  });
  const titleMutation = useMutation({
    mutationFn: createSessionTitle,
  });
  const { mutateAsync: createStream } = streamMutation;
  const { mutateAsync: createTitle } = titleMutation;
  const chatBlocked =
    status === "Streaming" ||
    status === "Approval required" ||
    status === "Resuming";

  const closeStream = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  useEffect(() => {
    return () => {
      closeStream();
    };
  }, [closeStream]);

  const loadSession = useCallback(
    (nextUuid: string) => {
      messageRef.current = "";
      setMessage("");
      setMentionRanges([]);
      setUiMessages(hydrateSessionMessages(userId, nextUuid));
      setStatus("Idle");
    },
    [userId],
  );

  const updateMessage = useCallback((nextValue: string) => {
    const previousValue = messageRef.current;
    messageRef.current = nextValue;
    setMessage(nextValue);
    setMentionRanges((current) =>
      syncFileMentionRanges({
        previousValue,
        nextValue,
        ranges: current,
      }),
    );
  }, []);

  const insertMentionRange = useCallback(
    (nextValue: string, range: FileMentionRange) => {
      const previousValue = messageRef.current;
      messageRef.current = nextValue;
      setMessage(nextValue);
      setMentionRanges((current) =>
        validFileMentionRanges(nextValue, [
          ...syncFileMentionRanges({
            previousValue,
            nextValue,
            ranges: current,
          }),
          range,
        ]),
      );
    },
    [],
  );

  const markResuming = useCallback(() => {
    setStatus("Resuming");
  }, []);

  const updateGeneratedSessionTitle = useCallback(
    async ({
      targetUserId,
      targetSessionUuid,
      targetSessionTitle,
      titleContext,
    }: {
      targetUserId: string;
      targetSessionUuid: string;
      targetSessionTitle: string | undefined;
      titleContext: string;
    }) => {
      if (targetSessionTitle !== DEFAULT_SESSION_TITLE || !titleContext.trim()) {
        return;
      }

      const requestKey = `${targetUserId}:${targetSessionUuid}`;
      if (titleRequestKeysRef.current.has(requestKey)) {
        return;
      }

      titleRequestKeysRef.current.add(requestKey);
      try {
        const response = await createTitle({
          userId: targetUserId,
          sessionUuid: targetSessionUuid,
          message: titleContext,
        });
        if (targetUserId === userId) {
          renameSession(targetSessionUuid, response.title);
        }
      } catch {
        // Session title generation must not block chat.
      } finally {
        titleRequestKeysRef.current.delete(requestKey);
      }
    },
    [createTitle, renameSession, userId],
  );

  const generateTitleForSession = useCallback(
    ({
      targetSessionUuid,
      targetSessionTitle,
    }: {
      targetSessionUuid: string;
      targetSessionTitle: string | undefined;
    }) => {
      const titleContext = firstCompletedExchangeTitleContext(
        getSessionHistory(userId, targetSessionUuid),
      );
      void updateGeneratedSessionTitle({
        targetUserId: userId,
        targetSessionUuid,
        targetSessionTitle,
        titleContext,
      });
    },
    [updateGeneratedSessionTitle, userId],
  );

  const submitMessage = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const displayMessage = trimFileMentionText(message, mentionRanges);
      const displayContent = displayMessage.value;
      const serializedContent = serializeFileMentions(
        displayContent,
        displayMessage.ranges,
      );

      if (!displayContent || chatBlocked) {
        return;
      }

      closeStream();
      onBeforeSubmit();
      messageRef.current = "";
      setMessage("");
      setMentionRanges([]);
      setStatus("Streaming");

      const history = getSessionHistory(userId, sessionUuid);
      const nextHistory: ChatMessage[] = [
        ...history,
        { role: "user", content: serializedContent },
      ];

      setUiMessages((current) => [
        ...current,
        userMessage(displayContent, displayMessage.ranges),
      ]);

      try {
        const streamId = await createStream({
          userId,
          sessionUuid,
          message: serializedContent,
          chatHistory: history,
        });
        onStreamCreated(streamId);

        let assistantText = "";
        const source = openChatEventSource(streamId, {
          onEvent(uiEvent) {
            if (uiEvent.kind === "assistant_delta" && uiEvent.text) {
              assistantText += uiEvent.text;
            }
            setUiMessages((current) =>
              appendAgentUiEvent(current, uiEvent, streamId),
            );
          },
          onHitlRequest(hitlRequest) {
            onHitlRequest(hitlRequest);
            setStatus("Approval required");
          },
          onHitlResumed() {
            onHitlResumed();
            setStatus("Streaming");
          },
          onDone() {
            const completedHistory = assistantText
              ? [
                  ...nextHistory,
                  { role: "assistant" as const, content: assistantText },
                ]
              : nextHistory;
            saveSessionHistory(userId, sessionUuid, completedHistory);
            touchSession(sessionUuid);
            if (userMessageCount(nextHistory) >= 2) {
              void updateGeneratedSessionTitle({
                targetUserId: userId,
                targetSessionUuid: sessionUuid,
                targetSessionTitle: currentSessionTitle,
                titleContext: buildSessionTitleContext({
                  userMessage: serializedContent,
                  assistantMessage: assistantText,
                }),
              });
            }
            setStatus("Idle");
            onStreamCleared();
            closeStream();
          },
          onError(errorText) {
            setUiMessages((current) => [...current, createErrorMessage(errorText)]);
            setStatus("Error");
            onStreamCleared();
            closeStream();
          },
        });

        eventSourceRef.current = source;
      } catch (error) {
        setUiMessages((current) => [
          ...current,
          createErrorMessage(error instanceof Error ? error.message : "Request failed."),
        ]);
        setStatus("Error");
        onStreamCleared();
      }
    },
    [
      chatBlocked,
      closeStream,
      currentSessionTitle,
      mentionRanges,
      message,
      onBeforeSubmit,
      onHitlRequest,
      onHitlResumed,
      onStreamCleared,
      onStreamCreated,
      sessionUuid,
      touchSession,
      updateGeneratedSessionTitle,
      userId,
      createStream,
    ],
  );

  return {
    chatBlocked,
    closeStream,
    generateTitleForSession,
    insertMentionRange,
    mentionRanges,
    loadSession,
    markResuming,
    message,
    setMessage: updateMessage,
    status,
    submitMessage,
    uiMessages,
  };
}

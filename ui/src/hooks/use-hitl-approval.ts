import { useCallback, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import type { HitlDecision, HitlRequest } from "@/lib/api";
import { submitHitlDecision } from "@/lib/api";
import {
  actionToDraft,
  type HitlDraft,
  type HitlMode,
  mergeDraftArgs,
} from "@/components/hitl/approval-model";

export function useHitlApproval({
  onResuming,
}: {
  onResuming(): void;
}) {
  const [activeStreamId, setActiveStreamId] = useState<string | null>(null);
  const [request, setRequest] = useState<HitlRequest | null>(null);
  const [mode, setMode] = useState<HitlMode>("review");
  const [drafts, setDrafts] = useState<HitlDraft[]>([]);
  const [rejectMessage, setRejectMessage] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const decisionMutation = useMutation({
    mutationFn: ({
      streamId,
      decisions,
    }: {
      streamId: string;
      decisions: HitlDecision[];
    }) => submitHitlDecision({ streamId, decisions }),
    onSuccess: () => {
      clearDialogState();
      onResuming();
    },
    onError: (error) => {
      setStatus(error instanceof Error ? error.message : "Approval failed.");
    },
  });
  const {
    isPending,
    mutateAsync: submitDecision,
    reset: resetDecision,
  } = decisionMutation;

  const beginStream = useCallback((streamId: string) => {
    setActiveStreamId(streamId);
  }, []);

  const clearDialogState = useCallback(() => {
    setRequest(null);
    setMode("review");
    setDrafts([]);
    setRejectMessage("");
    setStatus(null);
    resetDecision();
  }, [resetDecision]);

  const clearState = useCallback(() => {
    setActiveStreamId(null);
    clearDialogState();
  }, [clearDialogState]);

  const openRequest = useCallback((hitlRequest: HitlRequest) => {
    setRequest(hitlRequest);
    setMode("review");
    setDrafts(hitlRequest.actions.map(actionToDraft));
    setRejectMessage("");
    setStatus(null);
  }, []);

  const updateDraft = useCallback(
    (index: number, field: keyof HitlDraft, value: string) => {
      setDrafts((current) => {
        const next = [...current];
        next[index] = {
          ...(next[index] ?? {
            path: "",
            content: "",
            instruction: "",
          }),
          [field]: value,
        };
        return next;
      });
    },
    [],
  );

  const submit = useCallback(
    async (decisionType: HitlDecision["type"]) => {
      if (!activeStreamId || !request) {
        return;
      }

      let decisions: HitlDecision[];
      try {
        if (decisionType === "approve") {
          decisions = request.actions.map(() => ({ type: "approve" }));
        } else if (decisionType === "reject") {
          decisions = request.actions.map(() => ({
            type: "reject",
            message: rejectMessage.trim() || "Rejected by user.",
          }));
        } else {
          decisions = request.actions.map((action, index) => {
            const draft = drafts[index] ?? actionToDraft(action);
            return {
              type: "edit",
              edited_action: {
                name: action.name,
                args: mergeDraftArgs(action, draft),
              },
            };
          });
        }
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "Invalid approval input.");
        return;
      }

      setStatus("승인 결정을 제출하는 중입니다...");
      try {
        await submitDecision({ streamId: activeStreamId, decisions });
      } catch {
        // The mutation onError handler publishes the user-visible status.
      }
    },
    [activeStreamId, drafts, rejectMessage, request, submitDecision],
  );

  return {
    beginStream,
    clearDialogState,
    clearState,
    drafts,
    mode,
    openRequest,
    rejectMessage,
    request,
    setMode,
    setRejectMessage,
    status,
    submit,
    submitting: isPending,
    updateDraft,
  };
}

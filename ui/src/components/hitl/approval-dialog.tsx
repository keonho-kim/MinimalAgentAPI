import { Check, Loader2, Pencil, ShieldCheck, X } from "lucide-react";
import { memo } from "react";

import type { HitlRequest } from "@/lib/api";
import {
  actionToDraft,
  type HitlDraft,
  type HitlMode,
} from "@/components/hitl/approval-model";
import { ApprovalActionCard } from "@/components/hitl/approval-action-card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

export const HitlApprovalDialog = memo(function HitlApprovalDialog({
  request,
  mode,
  drafts,
  rejectMessage,
  status,
  submitting,
  onModeChange,
  onDraftChange,
  onRejectMessageChange,
  onApprove,
  onApproveAgent,
  onApproveCore,
  onSubmitEdit,
  onReject,
}: {
  request: HitlRequest | null;
  mode: HitlMode;
  drafts: HitlDraft[];
  rejectMessage: string;
  status: string | null;
  submitting: boolean;
  onModeChange(mode: HitlMode): void;
  onDraftChange(index: number, field: keyof HitlDraft, value: string): void;
  onRejectMessageChange(value: string): void;
  onApprove(): void;
  onApproveAgent(): void;
  onApproveCore(): void;
  onSubmitEdit(): void;
  onReject(): void;
}) {
  const actions = request?.actions ?? [];
  const canApprove = actions.every((action) =>
    action.allowed_decisions.includes("approve"),
  );
  const canEdit = actions.every((action) =>
    action.allowed_decisions.includes("edit"),
  );
  const canReject = actions.every((action) =>
    action.allowed_decisions.includes("reject"),
  );

  return (
    <Dialog open={Boolean(request)}>
      <DialogContent className="max-w-3xl p-0" showClose={false}>
        <DialogHeader className="border-b px-5 py-4 pr-10">
          <div className="flex items-center gap-2">
            <ShieldCheck className="text-muted-foreground" data-icon="inline-start" />
            <DialogTitle>승인이 필요한 작업</DialogTitle>
          </div>
          <DialogDescription>
            에이전트가 작업을 계속하기 전에 파일 변경 승인이 필요합니다.
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 overflow-y-auto px-5 py-4">
          <div className="flex flex-col gap-3">
            {actions.map((action, index) => (
              <ApprovalActionCard
                action={action}
                draft={drafts[index] ?? actionToDraft(action)}
                index={index}
                key={`${action.name}-${index}`}
                mode={mode}
                onDraftChange={onDraftChange}
              />
            ))}
          </div>

          {mode === "reject" ? (
            <div className="mt-4">
              <label className="mb-2 block text-sm font-medium" htmlFor="hitl-reject">
                거절 사유
              </label>
              <Textarea
                className="min-h-20"
                id="hitl-reject"
                placeholder="예: 이 파일은 아직 수정하면 안 됩니다."
                value={rejectMessage}
                onChange={(event) => onRejectMessageChange(event.target.value)}
              />
            </div>
          ) : null}

          {status ? <p className="mt-3 text-xs text-muted-foreground">{status}</p> : null}
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2 border-t px-5 py-4">
          {mode === "review" ? (
            <>
              <Button
                disabled={!canEdit || submitting}
                variant="outline"
                onClick={() => onModeChange("edit")}
              >
                <Pencil data-icon="inline-start" />
                내용 수정
              </Button>
              <Button
                disabled={!canReject || submitting}
                variant="outline"
                onClick={() => onModeChange("reject")}
              >
                <X data-icon="inline-start" />
                거절
              </Button>
              <Button disabled={!canApprove || submitting} onClick={onApprove}>
                {submitting ? (
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                ) : (
                  <Check data-icon="inline-start" />
                )}
                승인
              </Button>
              {request?.approval_scope ? (
                <Button
                  disabled={!canApprove || submitting}
                  variant="outline"
                  onClick={onApproveAgent}
                >
                  <ShieldCheck data-icon="inline-start" />
                  이 에이전트 항상 승인
                </Button>
              ) : null}
              <Button
                disabled={!canApprove || submitting}
                variant="outline"
                onClick={onApproveCore}
              >
                <ShieldCheck data-icon="inline-start" />
                모든 에이전트 자동 승인
              </Button>
            </>
          ) : null}

          {mode === "edit" ? (
            <>
              <Button
                disabled={submitting}
                variant="ghost"
                onClick={() => onModeChange("review")}
              >
                돌아가기
              </Button>
              <Button disabled={submitting} onClick={onSubmitEdit}>
                {submitting ? (
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                ) : (
                  <Pencil data-icon="inline-start" />
                )}
                수정하여 승인
              </Button>
            </>
          ) : null}

          {mode === "reject" ? (
            <>
              <Button
                disabled={submitting}
                variant="ghost"
                onClick={() => onModeChange("review")}
              >
                돌아가기
              </Button>
              <Button disabled={submitting} variant="destructive" onClick={onReject}>
                {submitting ? (
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                ) : (
                  <X data-icon="inline-start" />
                )}
                거절
              </Button>
            </>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
});

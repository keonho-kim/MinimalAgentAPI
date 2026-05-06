import { memo } from "react";

import type { HitlActionRequest } from "@/lib/api";
import type { HitlDraft, HitlMode } from "@/components/hitl/approval-model";
import {
  actionSummary,
  compactKeyValues,
  formatActionName,
  formatActionTarget,
  humanizeKey,
  replaceArg,
  shouldShowContentEditor,
  shouldShowInstructionEditor,
  stringArg,
} from "@/components/hitl/approval-display";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export const ApprovalActionCard = memo(function ApprovalActionCard({
  action,
  draft,
  index,
  mode,
  onDraftChange,
}: {
  action: HitlActionRequest;
  draft: HitlDraft;
  index: number;
  mode: HitlMode;
  onDraftChange(index: number, field: keyof HitlDraft, value: string): void;
}) {
  const target = formatActionTarget(action);
  const summary = actionSummary(action);

  return (
    <div className="rounded-md border bg-background p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold">{formatActionName(action.name)}</p>
          <p className="mt-1 truncate font-mono text-xs text-muted-foreground">
            {target}
          </p>
        </div>
        <Badge className="bg-card text-muted-foreground" variant="outline">
          파일 변경
        </Badge>
      </div>

      <div className="mt-3 grid gap-3 text-sm">
        <InfoRow label="작업 설명" value={action.description || summary.description} />
        <InfoRow label="변경 요약" value={summary.change} />
      </div>

      {mode === "edit" ? (
        <div className="mt-4 grid gap-3">
          <label className="grid gap-1.5 text-sm">
            <span className="font-medium">대상 파일</span>
            <Input
              value={draft.path}
              onChange={(event) => onDraftChange(index, "path", event.target.value)}
            />
          </label>
          {shouldShowContentEditor(action) ? (
            <label className="grid gap-1.5 text-sm">
              <span className="font-medium">파일 내용</span>
              <Textarea
                className="min-h-40 font-mono text-xs"
                value={draft.content}
                onChange={(event) =>
                  onDraftChange(index, "content", event.target.value)
                }
              />
            </label>
          ) : null}
          {shouldShowInstructionEditor(action) ? (
            <label className="grid gap-1.5 text-sm">
              <span className="font-medium">수정 지시</span>
              <Textarea
                className="min-h-28"
                value={draft.instruction}
                onChange={(event) =>
                  onDraftChange(index, "instruction", event.target.value)
                }
              />
            </label>
          ) : null}
          {!shouldShowContentEditor(action) && !shouldShowInstructionEditor(action) ? (
            <p className="rounded-md border bg-card p-3 text-sm text-muted-foreground">
              이 작업은 대상 파일만 수정할 수 있습니다. 세부 값은 기존 요청을 유지합니다.
            </p>
          ) : null}
        </div>
      ) : (
        <ActionPreview action={action} />
      )}
    </div>
  );
});

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[6rem_minmax(0,1fr)]">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <span className="min-w-0 whitespace-pre-wrap leading-6">{value}</span>
    </div>
  );
}

function ActionPreview({ action }: { action: HitlActionRequest }) {
  const args = action.args ?? {};
  const content = stringArg(args, "content");
  const instruction = stringArg(args, "instruction");
  const oldText = replaceArg(args, "old");
  const newText = replaceArg(args, "new");
  const values = compactKeyValues(args);

  if (action.name === "write_file" && content) {
    return (
      <div className="mt-4">
        <p className="mb-2 text-sm font-medium">작성될 내용</p>
        <div className="max-h-56 overflow-auto rounded-md border bg-card p-3 font-mono text-xs leading-5 whitespace-pre-wrap">
          {content}
        </div>
      </div>
    );
  }

  if (oldText || newText || instruction) {
    return (
      <div className="mt-4 grid gap-2 rounded-md border bg-card p-3 text-sm">
        {oldText ? <InfoRow label="찾을 내용" value={oldText} /> : null}
        {newText ? <InfoRow label="바꿀 내용" value={newText} /> : null}
        {instruction ? <InfoRow label="수정 지시" value={instruction} /> : null}
      </div>
    );
  }

  if (values.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 grid gap-2 rounded-md border bg-card p-3 text-sm">
      {values.map(([key, value]) => (
        <InfoRow key={key} label={humanizeKey(key)} value={value} />
      ))}
    </div>
  );
}

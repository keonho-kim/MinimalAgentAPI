import { Check, Loader2, Pencil, ShieldCheck, X } from "lucide-react";

import type { HitlActionRequest, HitlRequest } from "@/lib/api";
import {
  actionToDraft,
  type HitlDraft,
  type HitlMode,
} from "@/components/hitl/approval-model";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export function HitlApprovalDialog({
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
}

function ApprovalActionCard({
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
}

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

function formatActionTarget(action: HitlActionRequest) {
  const path = stringArg(action.args, "file_path") ?? stringArg(action.args, "path");
  return path ?? "대상 파일 정보 없음";
}

function stringArg(args: Record<string, unknown>, key: string) {
  const value = args[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function formatActionName(name: string) {
  if (name === "write_file") {
    return "파일 작성";
  }
  if (name === "edit_file") {
    return "파일 수정";
  }
  if (name === "edit_docx") {
    return "DOCX 파일 수정";
  }
  if (name === "edit_hwpx") {
    return "HWPX 파일 수정";
  }
  if (name === "edit_pptx") {
    return "PPTX 파일 수정";
  }
  if (name === "edit_xlsx") {
    return "XLSX 파일 수정";
  }
  return name.replaceAll("_", " ");
}

function actionSummary(action: HitlActionRequest) {
  const target = formatActionTarget(action);
  if (action.name === "write_file") {
    return {
      description: `${target} 파일을 새로 작성하거나 덮어씁니다.`,
      change: summarizeText(stringArg(action.args, "content"), "파일 내용을 저장합니다."),
    };
  }
  if (action.name === "edit_file") {
    return {
      description: `${target} 파일의 내용을 수정합니다.`,
      change:
        stringArg(action.args, "instruction") ??
        summarizeReplace(action.args) ??
        "요청한 내용에 맞게 파일을 수정합니다.",
    };
  }
  if (isOfficeEditTool(action.name)) {
    return {
      description: `${target} 문서를 수정합니다.`,
      change:
        stringArg(action.args, "instruction") ??
        "문서 편집 workflow를 실행해 수정본을 생성합니다.",
    };
  }
  return {
    description: `${target}에 대해 ${formatActionName(action.name)} 작업을 실행합니다.`,
    change: compactKeyValues(action.args)
      .map(([key, value]) => `${humanizeKey(key)}: ${value}`)
      .join("\n") || "작업 요청 값을 유지합니다.",
  };
}

function summarizeReplace(args: Record<string, unknown>) {
  const oldText = replaceArg(args, "old");
  const newText = replaceArg(args, "new");
  if (oldText && newText) {
    return `"${oldText}" 내용을 "${newText}"로 바꿉니다.`;
  }
  return null;
}

function replaceArg(args: Record<string, unknown>, direction: "old" | "new") {
  const candidates =
    direction === "old"
      ? ["old_text", "OLD_TEXT", "old_string", "old_str"]
      : ["new_text", "NEW_TEXT", "new_string", "new_str"];
  for (const key of candidates) {
    const value = stringArg(args, key);
    if (value) {
      return value;
    }
  }
  return null;
}

function summarizeText(value: string | null, fallback: string) {
  if (!value) {
    return fallback;
  }
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > 160 ? `${normalized.slice(0, 160)}...` : normalized;
}

function compactKeyValues(args: Record<string, unknown>) {
  return Object.entries(args)
    .filter(([key, value]) => {
      return (
        !["content", "path", "file_path", "instruction"].includes(key) &&
        (typeof value === "string" ||
          typeof value === "number" ||
          typeof value === "boolean")
      );
    })
    .map(([key, value]) => [key, summarizeText(String(value), "")] as const)
    .filter(([, value]) => value);
}

function humanizeKey(key: string) {
  return key
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function shouldShowContentEditor(action: HitlActionRequest) {
  return action.name === "write_file" || "content" in action.args;
}

function shouldShowInstructionEditor(action: HitlActionRequest) {
  return isOfficeEditTool(action.name) || "instruction" in action.args;
}

function isOfficeEditTool(name: string) {
  return ["edit_docx", "edit_hwpx", "edit_pptx", "edit_xlsx"].includes(name);
}

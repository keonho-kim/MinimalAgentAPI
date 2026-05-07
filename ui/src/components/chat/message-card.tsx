import { lazy, memo, Suspense } from "react";

import type { AgentUiEvent } from "@/lib/stream";
import { activityDetailLines } from "@/lib/activity-summary";
import type { UiMessage } from "@/lib/chat-messages";
import {
  serializeFileMentions,
  splitLeadingFileMentionAttachments,
  splitLeadingMarkdownFileMentionAttachments,
} from "@/lib/file-mentions";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

const MessageRenderer = lazy(() =>
  import("@/components/message-renderer").then((module) => ({
    default: module.MessageRenderer,
  })),
);

export const MessageCard = memo(function MessageCard({ item }: { item: UiMessage }) {
  const hasFileMentions = item.role === "user" && Boolean(item.fileMentions?.length);
  const rangedFileMessage =
    hasFileMentions
      ? splitLeadingFileMentionAttachments({
          value: item.content,
          ranges: item.fileMentions ?? [],
        })
      : null;
  const markdownFileMessage =
    !rangedFileMessage && item.role === "user"
      ? splitLeadingMarkdownFileMentionAttachments(item.content)
      : null;
  const fileMessage = rangedFileMessage ?? markdownFileMessage;
  const renderContent = rangedFileMessage
    ? serializeFileMentions(rangedFileMessage.value, rangedFileMessage.ranges)
    : markdownFileMessage
      ? markdownFileMessage.value
      : item.content;
  const variant =
    item.kind === "error"
      ? "border-destructive/30 bg-destructive/5 text-destructive"
      : item.kind === "reasoning"
        ? "border-border bg-muted text-muted-foreground"
        : item.kind === "activity"
          ? "border-border bg-muted/40 text-foreground"
          : hasFileMentions
            ? "ml-auto max-w-[88%] bg-card sm:max-w-[80%]"
            : item.role === "user"
              ? "ml-auto max-w-[88%] border-primary bg-primary text-primary-foreground sm:max-w-[80%]"
              : "mr-auto max-w-[88%] bg-card sm:max-w-[80%]";

  return (
    <Card className={variant}>
      <CardContent className="p-3.5 sm:p-4">
        {item.kind === "activity" && item.activity ? (
          <ActivityMessage activity={item.activity} fallback={item.content} />
        ) : fileMessage?.attachments.length ? (
          <UserFileMessage
            attachments={fileMessage.attachments}
            content={renderContent}
          />
        ) : (
          <RenderedMessage content={renderContent} role={item.role} />
        )}
      </CardContent>
    </Card>
  );
});

function RenderedMessage({
  content,
  role,
}: {
  content: string;
  role: "user" | "assistant";
}) {
  return (
    <Suspense
      fallback={
        <div className="message-renderer whitespace-pre-wrap">{content}</div>
      }
    >
      <MessageRenderer content={content} role={role} />
    </Suspense>
  );
}

function UserFileMessage({
  attachments,
  content,
}: {
  attachments: { id: string; label: string; href: string }[];
  content: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {attachments.map((attachment) => (
          <span
            className="chat-file-attachment-pill"
            key={attachment.id}
            title={attachment.label}
          >
            {attachment.label}
          </span>
        ))}
      </div>
      {content ? <RenderedMessage content={content} role="user" /> : null}
    </div>
  );
}

function ActivityMessage({
  activity,
  fallback,
}: {
  activity: Extract<AgentUiEvent, { kind: "activity" }>;
  fallback: string;
}) {
  const summary = objectSummary(activity.summary);
  const details = activityDetailLines(summary);
  const intermediateTexts = activityIntermediateTexts(summary);
  const activitySteps = activityStepDetails(summary);
  const groupedCount = numberValue(summary.groupedCount);

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium">
          {activity.label || activity.name || "Agent activity"}
        </span>
        {groupedCount && groupedCount > 1 ? (
          <Badge
            variant="outline"
            className="h-5 px-1.5 text-[10px] text-muted-foreground"
          >
            {groupedCount}회
          </Badge>
        ) : null}
        {activity.status ? (
          <Badge
            variant="outline"
            className="h-5 px-1.5 text-[10px] text-muted-foreground"
          >
            {formatActivityStatus(activity.status)}
          </Badge>
        ) : null}
      </div>
      <p className="text-xs leading-5 text-muted-foreground">
        {activity.message || fallback}
      </p>
      {details.length ? (
        <div className="space-y-1 text-[11px] leading-5 text-muted-foreground">
          {details.map((detail) => (
            <div key={detail}>{detail}</div>
          ))}
        </div>
      ) : null}
      {activitySteps.length ? (
        <details className="rounded-md border border-border bg-background/50 px-2.5 py-2 text-[11px]">
          <summary className="cursor-pointer font-medium text-muted-foreground">
            세부 단계 보기 {activitySteps.length}개
          </summary>
          <div className="mt-2 space-y-1.5">
            {activitySteps.map((step) => (
              <div
                className="grid gap-1 border-l border-border pl-2 text-muted-foreground sm:grid-cols-[9rem_1fr]"
                key={step.id}
              >
                <div className="flex items-center gap-1.5">
                  <span className="truncate font-medium text-foreground">
                    {step.label || step.name}
                  </span>
                  {step.status ? (
                    <span className="shrink-0 text-[10px]">
                      {formatActivityStatus(step.status)}
                    </span>
                  ) : null}
                </div>
                {step.message ? <div>{step.message}</div> : null}
              </div>
            ))}
          </div>
        </details>
      ) : null}
      {intermediateTexts.length ? (
        <details className="rounded-md border border-border bg-background/50 px-2.5 py-2 text-[11px]">
          <summary className="cursor-pointer font-medium text-muted-foreground">
            중간 응답 보기
            {intermediateTexts.length > 1 ? ` ${intermediateTexts.length}개` : ""}
          </summary>
          <div className="mt-2 space-y-3 text-foreground">
            {intermediateTexts.map((text, index) => (
              <RenderedMessage
                content={text}
                key={`${index}:${text.slice(0, 24)}`}
                role="assistant"
              />
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}

function objectSummary(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function numberValue(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function activityIntermediateTexts(summary: Record<string, unknown>) {
  const texts = Array.isArray(summary.intermediateTexts)
    ? summary.intermediateTexts
    : [summary.intermediateText];
  return texts.filter(
    (text): text is string => typeof text === "string" && text.trim().length > 0,
  );
}

function activityStepDetails(summary: Record<string, unknown>) {
  const steps = Array.isArray(summary.activitySteps) ? summary.activitySteps : [];
  return steps.filter(
    (step): step is {
      id: string;
      name?: string;
      label?: string;
      message?: string;
      status?: string;
    } =>
      Boolean(step) &&
      typeof step === "object" &&
      !Array.isArray(step) &&
      typeof (step as Record<string, unknown>).id === "string",
  );
}

function formatActivityStatus(status: string) {
  if (status === "running") {
    return "진행 중";
  }
  if (status === "completed") {
    return "완료";
  }
  if (status === "error") {
    return "오류";
  }
  if (status === "pending") {
    return "준비";
  }
  return status;
}

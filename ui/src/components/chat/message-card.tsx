import { lazy, Suspense } from "react";

import type { ChatMessage } from "@/lib/api";
import type { AgentUiEvent } from "@/lib/stream";
import { activityDetailLines } from "@/lib/activity-summary";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

const MessageRenderer = lazy(() =>
  import("@/components/message-renderer").then((module) => ({
    default: module.MessageRenderer,
  })),
);

export type UiMessage = ChatMessage & {
  id: string;
  kind?: "normal" | "reasoning" | "activity" | "error";
  activity?: Extract<AgentUiEvent, { kind: "activity" }>;
};

export function MessageCard({ item }: { item: UiMessage }) {
  const variant =
    item.kind === "error"
      ? "border-destructive/30 bg-destructive/5 text-destructive"
      : item.kind === "reasoning"
        ? "border-border bg-muted text-muted-foreground"
        : item.kind === "activity"
          ? "border-accent bg-accent text-accent-foreground"
          : item.role === "user"
            ? "ml-auto max-w-[88%] border-primary bg-primary text-primary-foreground sm:max-w-[80%]"
            : "mr-auto max-w-[88%] bg-card sm:max-w-[80%]";

  return (
    <Card className={variant}>
      <CardContent className="p-3.5 sm:p-4">
        {item.kind === "activity" && item.activity ? (
          <ActivityMessage activity={item.activity} fallback={item.content} />
        ) : (
          <Suspense
            fallback={
              <div className="message-renderer whitespace-pre-wrap">
                {item.content}
              </div>
            }
          >
            <MessageRenderer content={item.content} role={item.role} />
          </Suspense>
        )}
      </CardContent>
    </Card>
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
  const groupedCount = numberValue(summary.groupedCount);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium">
          {activity.label || activity.name || "Agent activity"}
        </span>
        {groupedCount && groupedCount > 1 ? (
          <Badge variant="outline" className="h-5 px-1.5 text-[11px]">
            {groupedCount}회
          </Badge>
        ) : null}
        {activity.status ? (
          <Badge variant="outline" className="h-5 px-1.5 text-[11px]">
            {formatActivityStatus(activity.status)}
          </Badge>
        ) : null}
      </div>
      <p className="text-sm leading-6">{activity.message || fallback}</p>
      {details.length ? (
        <div className="space-y-1 text-xs leading-5 text-muted-foreground">
          {details.map((detail) => (
            <div key={detail}>{detail}</div>
          ))}
        </div>
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

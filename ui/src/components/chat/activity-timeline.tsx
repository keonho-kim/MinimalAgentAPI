import { lazy, memo, Suspense } from "react";
import {
  Bot,
  ChevronDown,
  FilePenLine,
  FilePlus,
  FileText,
  ListTree,
  LoaderCircle,
  Search,
  Terminal,
  Wrench,
} from "lucide-react";

import type { ActivityBlockMessage } from "@/lib/chat-messages";
import {
  activityTimelineSummary,
  hasRunningActivity,
} from "@/lib/activity-timeline";
import type { ActivityTraceCategory } from "@/lib/activity-timeline";

const MessageRenderer = lazy(() =>
  import("@/components/message-renderer").then((module) => ({
    default: module.MessageRenderer,
  })),
);

export const ActivityTimeline = memo(function ActivityTimeline({
  item,
}: {
  item: ActivityBlockMessage;
}) {
  const running = hasRunningActivity(item.entries);

  return (
    <details className="group py-0.5 text-[13px] text-muted-foreground">
      <summary className="inline-flex max-w-full cursor-pointer list-none items-center gap-2 align-baseline">
        {running ? (
          <LoaderCircle className="size-3.5 shrink-0 animate-spin" />
        ) : (
          <TimelineIcon category={primaryCategory(item)} />
        )}
        <span className="min-w-0 truncate">
          {activityTimelineSummary(item.entries)}
        </span>
        {running ? (
          <span className="shrink-0 text-[11px]">진행 중</span>
        ) : null}
        <ChevronDown className="size-3 shrink-0 transition-transform group-open:rotate-180" />
      </summary>
      <div className="mt-1.5 space-y-1 pl-5 font-mono text-[12px] leading-5 text-muted-foreground/80">
        {item.entries.map((entry) =>
          entry.category === "intermediate" ? (
            <div className="font-sans text-foreground" key={entry.id}>
              <Suspense fallback={<div>{entry.detail}</div>}>
                <MessageRenderer content={entry.detail} role="assistant" />
              </Suspense>
            </div>
          ) : (
            <div className="flex min-w-0 items-baseline gap-2" key={entry.id}>
              <span className="min-w-0 whitespace-normal break-words">
                {entry.detail}
              </span>
              {entry.status && entry.status !== "completed" ? (
                <span className="shrink-0 text-[11px]">
                  {formatActivityStatus(entry.status)}
                </span>
              ) : null}
            </div>
          ),
        )}
      </div>
    </details>
  );
});

function primaryCategory(item: ActivityBlockMessage) {
  return (
    item.entries.find((entry) => entry.category !== "intermediate")?.category ??
    "other"
  );
}

function TimelineIcon({ category }: { category: ActivityTraceCategory }) {
  const className = "size-3.5 shrink-0";
  if (category === "search") {
    return <Search className={className} />;
  }
  if (category === "list") {
    return <ListTree className={className} />;
  }
  if (category === "command") {
    return <Terminal className={className} />;
  }
  if (category === "file-create") {
    return <FilePlus className={className} />;
  }
  if (category === "file-edit") {
    return <FilePenLine className={className} />;
  }
  if (category === "file-read") {
    return <FileText className={className} />;
  }
  if (category === "subagent") {
    return <Bot className={className} />;
  }
  return <Wrench className={className} />;
}

function formatActivityStatus(status: string) {
  if (status === "running") {
    return "진행 중";
  }
  if (status === "error") {
    return "오류";
  }
  if (status === "pending") {
    return "준비";
  }
  return status;
}

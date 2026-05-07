import { Plus, Trash2 } from "lucide-react";
import { memo, useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";

import wordmarkUrl from "../../../assets/logo/logo.png";

import type { SessionSummary } from "@/store/session-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export const AppSidebar = memo(function AppSidebar({
  userId,
  sessionUuid,
  sessions,
  onNewSession,
  onRemoveSession,
  onSwitchSession,
  onUserIdChange,
}: {
  userId: string;
  sessionUuid: string;
  sessions: SessionSummary[];
  onNewSession(): void;
  onRemoveSession(uuid: string): void;
  onSwitchSession(uuid: string): void;
  onUserIdChange(userId: string): void;
}) {
  return (
    <aside className="hidden h-full min-h-0 w-72 shrink-0 border-r bg-card px-4 py-4 lg:flex lg:flex-col">
      <div className="flex min-h-9 items-center">
        <img
          alt="LG CNS"
          className="h-8 w-auto max-w-[10.5rem] object-contain"
          src={wordmarkUrl}
        />
      </div>

      <div className="mt-6 flex flex-col gap-2">
        <label
          className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground"
          htmlFor="user-id"
        >
          User ID
        </label>
        <Input
          id="user-id"
          value={userId}
          onChange={(event) => onUserIdChange(event.target.value)}
        />
      </div>

      <Separator className="my-5" />

      <div className="flex items-center justify-between">
        <h2 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Sessions
        </h2>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button size="icon" variant="ghost" onClick={onNewSession}>
              <Plus data-icon="inline-start" />
              <span className="sr-only">New session</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>New session</TooltipContent>
        </Tooltip>
      </div>

      <ScrollArea className="mt-2 min-h-0 flex-1">
        <div className="flex flex-col gap-0.5 pr-1">
          {sessions.map((session) => (
            <div
              key={session.uuid}
              className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-0.5"
            >
              <Button
                className="session-title-button h-7 w-full min-w-0 justify-start overflow-hidden px-2 text-xs"
                variant={session.uuid === sessionUuid ? "secondary" : "ghost"}
                onClick={() => onSwitchSession(session.uuid)}
                title={session.title}
              >
                <SessionTitleText title={session.title} />
              </Button>
              <Button
                className="size-7 text-muted-foreground hover:text-foreground"
                size="icon"
                variant="ghost"
                onClick={(event) => {
                  event.stopPropagation();
                  onRemoveSession(session.uuid);
                }}
              >
                <Trash2 data-icon="inline-start" />
                <span className="sr-only">Delete session</span>
              </Button>
            </div>
          ))}
        </div>
      </ScrollArea>
    </aside>
  );
});

const SessionTitleText = memo(function SessionTitleText({ title }: { title: string }) {
  const viewportRef = useRef<HTMLSpanElement | null>(null);
  const trackRef = useRef<HTMLSpanElement | null>(null);
  const [overflow, setOverflow] = useState(0);

  useEffect(() => {
    const viewport = viewportRef.current;
    const track = trackRef.current;
    if (!viewport || !track) {
      return;
    }

    const measure = () => {
      const nextOverflow = Math.ceil(track.scrollWidth - viewport.clientWidth);
      setOverflow(nextOverflow > 1 ? nextOverflow : 0);
    };

    measure();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", measure);
      return () => window.removeEventListener("resize", measure);
    }

    const observer = new ResizeObserver(measure);
    observer.observe(viewport);
    observer.observe(track);
    return () => observer.disconnect();
  }, [title]);

  const duration = Math.min(9, Math.max(3.5, overflow / 18));
  const style = {
    "--session-title-shift": `-${overflow}px`,
    "--session-title-duration": `${duration}s`,
  } as CSSProperties;

  return (
    <span className="session-title-viewport" ref={viewportRef}>
      <span
        className="session-title-track"
        data-overflow={overflow > 0 ? "true" : "false"}
        ref={trackRef}
        style={style}
      >
        {title}
      </span>
    </span>
  );
});

import { PanelRightOpen, Plus } from "lucide-react";
import { memo } from "react";

import type { SessionSummary } from "@/store/session-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const ChatHeader = memo(function ChatHeader({
  currentTitle,
  sessionUuid,
  sessions,
  status,
  userId,
  onNewSession,
  onOpenFiles,
  onSwitchSession,
  onUserIdChange,
}: {
  currentTitle: string | undefined;
  sessionUuid: string;
  sessions: SessionSummary[];
  status: string;
  userId: string;
  onNewSession(): void;
  onOpenFiles(): void;
  onSwitchSession(uuid: string): void;
  onUserIdChange(userId: string): void;
}) {
  return (
    <header className="border-b bg-background px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold">Chat</p>
            <Badge className="bg-card text-muted-foreground" variant="outline">
              {status}
            </Badge>
          </div>
          <p className="truncate font-mono text-[11px] text-muted-foreground">
            {currentTitle ?? sessionUuid}
          </p>
        </div>
        <Button variant="outline" onClick={onOpenFiles}>
          <PanelRightOpen data-icon="inline-start" />
          Files
        </Button>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto] lg:hidden">
        <label className="sr-only" htmlFor="mobile-user-id">
          User ID
        </label>
        <Input
          className="h-8 text-xs"
          id="mobile-user-id"
          value={userId}
          onChange={(event) => onUserIdChange(event.target.value)}
        />
        <label className="sr-only" htmlFor="mobile-session">
          Session
        </label>
        <select
          className="h-8 min-w-0 rounded-md border bg-card px-3 text-xs text-foreground shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          id="mobile-session"
          value={sessionUuid}
          onChange={(event) => onSwitchSession(event.target.value)}
        >
          {sessions.map((session) => (
            <option key={session.uuid} value={session.uuid}>
              {session.title}
            </option>
          ))}
        </select>
        <Button className="h-8" size="sm" variant="secondary" onClick={onNewSession}>
          <Plus data-icon="inline-start" />
          New
        </Button>
      </div>
    </header>
  );
});

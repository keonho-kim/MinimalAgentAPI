import { memo, useLayoutEffect, useRef } from "react";

import type { UiMessage } from "@/lib/chat-messages";
import { ActivityTimeline } from "@/components/chat/activity-timeline";
import { MessageCard } from "@/components/chat/message-card";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

export const ChatMessageList = memo(function ChatMessageList({
  messages,
}: {
  messages: UiMessage[];
}) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    if (!messages.length) {
      return;
    }

    const frameId = window.requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ block: "end" });
    });

    return () => window.cancelAnimationFrame(frameId);
  }, [messages]);

  return (
    <ScrollArea className="min-h-0 flex-1 overflow-hidden">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-3 px-4 py-5 sm:py-6">
        {messages.length === 0 ? (
          <Card className="border-dashed bg-card/80">
            <CardHeader>
              <CardTitle>Start a session</CardTitle>
              <CardDescription>
                Send a message or upload files to work in the local workspace.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          messages.map((item) =>
            item.kind === "activity-block" ? (
              <ActivityTimeline item={item} key={item.id} />
            ) : (
              <MessageCard item={item} key={item.id} />
            ),
          )
        )}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
});

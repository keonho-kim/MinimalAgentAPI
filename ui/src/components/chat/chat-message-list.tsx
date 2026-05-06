import { memo } from "react";

import type { UiMessage } from "@/lib/chat-messages";
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
  return (
    <ScrollArea className="flex-1">
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
          messages.map((item) => <MessageCard key={item.id} item={item} />)
        )}
      </div>
    </ScrollArea>
  );
});

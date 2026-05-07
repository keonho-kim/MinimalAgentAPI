import { memo } from "react";

import type { UiChatMessage } from "@/lib/chat-messages";
import {
  serializeFileMentions,
  displayFileMentionLabel,
  splitLeadingFileMentionAttachments,
  splitLeadingMarkdownFileMentionAttachments,
} from "@/lib/file-mentions";
import { Card, CardContent } from "@/components/ui/card";
import { MessageRenderer } from "@/components/message-renderer";

export const MessageCard = memo(function MessageCard({
  item,
}: {
  item: UiChatMessage;
}) {
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
        : hasFileMentions
          ? "ml-auto max-w-[88%] bg-card sm:max-w-[80%]"
          : item.role === "user"
            ? "ml-auto max-w-[88%] border-primary bg-primary text-primary-foreground sm:max-w-[80%]"
            : "mr-auto max-w-[88%] bg-card sm:max-w-[80%]";

  return (
    <Card className={variant}>
      <CardContent className="p-3.5 sm:p-4">
        {fileMessage?.attachments.length ? (
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
  return <MessageRenderer content={content} role={role} />;
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
            title={displayFileMentionLabel(attachment.label)}
          >
            {displayFileMentionLabel(attachment.label)}
          </span>
        ))}
      </div>
      {content ? <RenderedMessage content={content} role="user" /> : null}
    </div>
  );
}

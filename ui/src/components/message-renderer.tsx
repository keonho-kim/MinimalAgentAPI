import { memo, useMemo } from "react";
import "katex/dist/katex.min.css";

import { renderSafeMarkdown } from "@/lib/markdown";
import { cn } from "@/lib/utils";

type MessageRendererProps = {
  className?: string;
  content: string;
  role: "user" | "assistant";
};

export const MessageRenderer = memo(function MessageRenderer({
  className,
  content,
  role,
}: MessageRendererProps) {
  const html = useMemo(() => renderSafeMarkdown(content), [content]);

  return (
    <div
      className={cn("message-renderer", className)}
      data-role={role}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
});

import { lazy, memo, Suspense, useEffect, useState } from "react";

import { ScrollArea } from "@/components/ui/scroll-area";

const MessageRenderer = lazy(() =>
  import("@/components/message-renderer").then((module) => ({
    default: module.MessageRenderer,
  })),
);

export const TextPreview = memo(function TextPreview({
  sourceUrl,
  mode,
}: {
  sourceUrl: string;
  mode: "markdown" | "text";
}) {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState("Loading text");

  useEffect(() => {
    let cancelled = false;

    async function loadText() {
      setStatus("Loading text");
      setContent("");
      const response = await fetch(sourceUrl);
      if (!response.ok) {
        throw new Error(`Text source failed: ${response.status}`);
      }
      const text = await response.text();
      if (cancelled) {
        return;
      }
      setContent(text);
      setStatus("Ready");
    }

    loadText().catch((error: unknown) => {
      setStatus(error instanceof Error ? error.message : "Text preview failed.");
    });

    return () => {
      cancelled = true;
    };
  }, [sourceUrl]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ScrollArea className="min-h-0 flex-1">
        <div className="mx-auto max-w-4xl p-5">
          {mode === "markdown" ? (
            <div className="rounded-md border bg-card p-5">
              <Suspense
                fallback={
                  <div className="message-renderer whitespace-pre-wrap">{content}</div>
                }
              >
                <MessageRenderer content={content} role="assistant" />
              </Suspense>
            </div>
          ) : (
            <pre className="min-h-80 whitespace-pre-wrap rounded-md border bg-card p-5 font-mono text-sm leading-6 text-foreground">
              {content}
            </pre>
          )}
        </div>
      </ScrollArea>
      <div className="border-t px-5 py-2 text-xs text-muted-foreground">{status}</div>
    </div>
  );
});

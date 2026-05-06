import DOMPurify from "dompurify";
import { memo, useEffect, useMemo, useState } from "react";

import {
  codeLanguageLabel,
  highlightCode,
  languageForFilename,
} from "@/lib/code-highlight";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";

export const CodePreview = memo(function CodePreview({
  sourceUrl,
  filename,
}: {
  sourceUrl: string;
  filename: string;
}) {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState("Loading code");
  const language = languageForFilename(filename);
  const highlighted = useMemo(
    () => DOMPurify.sanitize(highlightCode(content, language), {
      USE_PROFILES: { html: true },
      ADD_ATTR: ["class"],
    }),
    [content, language],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadCode() {
      setStatus("Loading code");
      setContent("");
      const response = await fetch(sourceUrl);
      if (!response.ok) {
        throw new Error(`Code source failed: ${response.status}`);
      }
      const text = await response.text();
      if (cancelled) {
        return;
      }
      setContent(text);
      setStatus("Ready");
    }

    loadCode().catch((error: unknown) => {
      setStatus(error instanceof Error ? error.message : "Code preview failed.");
    });

    return () => {
      cancelled = true;
    };
  }, [sourceUrl]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between border-b bg-card px-5 py-3">
        <span className="truncate font-mono text-sm text-muted-foreground">
          {filename}
        </span>
        <span className="rounded-md border bg-background px-2 py-1 text-xs font-medium text-muted-foreground">
          {codeLanguageLabel(language)}
        </span>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="p-5">
          <pre className="overflow-x-auto rounded-md border bg-card p-5 text-sm leading-6">
            <code
              className={cn("hljs block min-w-max font-mono", {
                [`language-${language}`]: Boolean(language),
              })}
              dangerouslySetInnerHTML={{ __html: highlighted }}
            />
          </pre>
        </div>
      </ScrollArea>
      <div className="border-t px-5 py-2 text-xs text-muted-foreground">{status}</div>
    </div>
  );
});

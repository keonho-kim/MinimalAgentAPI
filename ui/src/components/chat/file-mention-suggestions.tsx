import { FileText } from "lucide-react";
import { memo } from "react";

import type { FsListItem } from "@/lib/api";
import type { MentionStatus } from "@/hooks/use-file-mentions";
import { cn } from "@/lib/utils";

export const FileMentionSuggestions = memo(function FileMentionSuggestions({
  activeIndex,
  matches,
  status,
  onSelect,
}: {
  activeIndex: number;
  matches: FsListItem[];
  status: MentionStatus;
  onSelect(file: FsListItem): void;
}) {
  return (
    <div className="absolute bottom-full left-0 right-0 mb-2 rounded-lg border bg-card p-1 shadow-[0_8px_24px_rgba(31,35,32,0.08)]">
      {status === "loading" ? (
        <div className="px-3 py-2 text-sm text-muted-foreground">
          Searching files...
        </div>
      ) : null}
      {status === "error" ? (
        <div className="px-3 py-2 text-sm text-destructive">
          File search failed.
        </div>
      ) : null}
      {status === "ready" && matches.length === 0 ? (
        <div className="px-3 py-2 text-sm text-muted-foreground">
          No matching files.
        </div>
      ) : null}
      {matches.length > 0 ? (
        <div aria-label="File mention suggestions" role="listbox">
          {matches.map((file, index) => (
            <button
              aria-selected={index === activeIndex}
              className={cn(
                "flex w-full min-w-0 items-center gap-3 rounded-md px-3 py-2 text-left text-sm",
                index === activeIndex ? "bg-secondary" : "hover:bg-secondary",
              )}
              key={file.path}
              onMouseDown={(event) => {
                event.preventDefault();
                onSelect(file);
              }}
              role="option"
              type="button"
            >
              <FileText className="text-muted-foreground" data-icon="inline-start" />
              <span className="min-w-0">
                <span className="block truncate font-medium">{file.name}</span>
                <span className="block truncate font-mono text-[11px] text-muted-foreground">
                  {file.path}
                </span>
              </span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
});

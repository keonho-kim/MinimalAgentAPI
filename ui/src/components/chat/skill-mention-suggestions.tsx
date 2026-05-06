import { Sparkles } from "lucide-react";
import { memo } from "react";

import type { MentionStatus } from "@/hooks/use-file-mentions";
import type { SkillListItem } from "@/lib/api";
import { cn } from "@/lib/utils";

export const SkillMentionSuggestions = memo(function SkillMentionSuggestions({
  activeIndex,
  matches,
  status,
  onSelect,
}: {
  activeIndex: number;
  matches: SkillListItem[];
  status: MentionStatus;
  onSelect(skill: SkillListItem): void;
}) {
  return (
    <div className="absolute bottom-full left-0 right-0 mb-2 rounded-lg border bg-card p-1 shadow-[0_8px_24px_rgba(31,35,32,0.08)]">
      {status === "loading" ? (
        <div className="px-3 py-2 text-sm text-muted-foreground">
          Searching skills...
        </div>
      ) : null}
      {status === "error" ? (
        <div className="px-3 py-2 text-sm text-destructive">
          Skill search failed.
        </div>
      ) : null}
      {status === "ready" && matches.length === 0 ? (
        <div className="px-3 py-2 text-sm text-muted-foreground">
          No matching skills.
        </div>
      ) : null}
      {matches.length > 0 ? (
        <div aria-label="Skill mention suggestions" role="listbox">
          {matches.map((skill, index) => (
            <button
              aria-selected={index === activeIndex}
              className={cn(
                "flex w-full min-w-0 items-center gap-3 rounded-md px-3 py-2 text-left text-sm",
                index === activeIndex ? "bg-secondary" : "hover:bg-secondary",
              )}
              key={skill.path}
              onMouseDown={(event) => {
                event.preventDefault();
                onSelect(skill);
              }}
              role="option"
              type="button"
            >
              <Sparkles className="text-muted-foreground" data-icon="inline-start" />
              <span className="grid min-w-0 flex-1 grid-cols-[minmax(0,auto)_minmax(0,1fr)] items-baseline gap-2">
                <span className="truncate font-medium">{skill.name}</span>
                <span className="truncate text-xs text-muted-foreground">
                  {skill.description}
                </span>
              </span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
});

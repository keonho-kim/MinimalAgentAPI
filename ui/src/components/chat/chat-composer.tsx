import { Loader2, Send } from "lucide-react";
import { memo } from "react";
import type { FormEvent, KeyboardEvent, RefObject } from "react";

import type { FsListItem, SkillListItem } from "@/lib/api";
import type { FileMentionRange } from "@/lib/file-mentions";
import type { MentionStatus } from "@/hooks/use-file-mentions";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FileMentionSuggestions } from "@/components/chat/file-mention-suggestions";
import { SkillMentionSuggestions } from "@/components/chat/skill-mention-suggestions";

export const ChatComposer = memo(function ChatComposer({
  disabled,
  mentionActive,
  mentionIndex,
  mentionMatches,
  mentionStatus,
  message,
  mentionRanges,
  skillMentionActive,
  skillMentionIndex,
  skillMentionMatches,
  skillMentionStatus,
  textareaRef,
  onCursorSync,
  onMentionSelect,
  onSkillMentionSelect,
  onMessageChange,
  onMentionKeyDown,
  onSkillMentionKeyDown,
  onSubmit,
}: {
  disabled: boolean;
  mentionActive: boolean;
  mentionIndex: number;
  mentionMatches: FsListItem[];
  mentionStatus: MentionStatus;
  message: string;
  mentionRanges: FileMentionRange[];
  skillMentionActive: boolean;
  skillMentionIndex: number;
  skillMentionMatches: SkillListItem[];
  skillMentionStatus: MentionStatus;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  onCursorSync(element: HTMLTextAreaElement): void;
  onMentionSelect(file: FsListItem): void;
  onSkillMentionSelect(skill: SkillListItem): void;
  onMessageChange(value: string): void;
  onMentionKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void;
  onSkillMentionKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void;
  onSubmit(event: FormEvent<HTMLFormElement>): void;
}) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    onMentionKeyDown(event);
    if (event.defaultPrevented) {
      return;
    }
    onSkillMentionKeyDown(event);
    if (event.defaultPrevented) {
      return;
    }

    if (
      event.key !== "Enter" ||
      event.shiftKey ||
      disabled ||
      isComposing(event)
    ) {
      return;
    }

    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }

  return (
    <form className="border-t bg-card p-3 sm:p-4" onSubmit={onSubmit}>
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-2 sm:flex-row sm:gap-3">
        <div className="relative min-w-0 flex-1">
          {mentionActive ? (
            <FileMentionSuggestions
              activeIndex={mentionIndex}
              matches={mentionMatches}
              status={mentionStatus}
              onSelect={onMentionSelect}
            />
          ) : null}
          {skillMentionActive ? (
            <SkillMentionSuggestions
              activeIndex={skillMentionIndex}
              matches={skillMentionMatches}
              status={skillMentionStatus}
              onSelect={onSkillMentionSelect}
            />
          ) : null}
          <Textarea
            className="min-h-20 resize-none"
            onChange={(event) => {
              onMessageChange(event.target.value);
              onCursorSync(event.currentTarget);
            }}
            onClick={(event) => onCursorSync(event.currentTarget)}
            onKeyDown={handleKeyDown}
            onKeyUp={(event) => onCursorSync(event.currentTarget)}
            placeholder="메시지를 입력하세요"
            ref={textareaRef}
            value={message}
          />
          {mentionRanges.length ? (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {mentionRanges.map((range) => (
                <span
                  className={
                    range.kind === "skill"
                      ? "skill-mention-pill"
                      : "file-mention-pill"
                  }
                  key={range.id}
                >
                  {range.label}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <Button
          className="h-10 self-stretch px-5 sm:h-20"
          disabled={disabled}
          type="submit"
        >
          {disabled ? (
            <Loader2 className="animate-spin" data-icon="inline-start" />
          ) : (
            <Send data-icon="inline-start" />
          )}
          Send
        </Button>
      </div>
    </form>
  );
});

function isComposing(event: KeyboardEvent<HTMLTextAreaElement>) {
  return event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229;
}

import { Loader2, Paperclip, Send, X } from "lucide-react";
import { memo, useRef, useState } from "react";
import type {
  ChangeEvent,
  DragEvent,
  FormEvent,
  KeyboardEvent,
  RefObject,
} from "react";

import type { FsListItem, SkillListItem } from "@/lib/api";
import type {
  FileMentionAttachment,
  FileMentionRange,
} from "@/lib/file-mentions";
import type { MentionStatus } from "@/hooks/use-file-mentions";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FileMentionSuggestions } from "@/components/chat/file-mention-suggestions";
import { SkillMentionSuggestions } from "@/components/chat/skill-mention-suggestions";
import { cn } from "@/lib/utils";

export const ChatComposer = memo(function ChatComposer({
  disabled,
  mentionActive,
  mentionIndex,
  mentionMatches,
  mentionStatus,
  message,
  mentionRanges,
  uploadAttachments,
  uploadError,
  uploadPending,
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
  onUploadAttachmentRemove,
  onUploadFiles,
  onSubmit,
}: {
  disabled: boolean;
  mentionActive: boolean;
  mentionIndex: number;
  mentionMatches: FsListItem[];
  mentionStatus: MentionStatus;
  message: string;
  mentionRanges: FileMentionRange[];
  uploadAttachments: FileMentionAttachment[];
  uploadError: string | null;
  uploadPending: boolean;
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
  onUploadAttachmentRemove(id: string): void;
  onUploadFiles(files: File[]): void;
  onSubmit(event: FormEvent<HTMLFormElement>): void;
}) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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

  function handleDragOver(event: DragEvent<HTMLFormElement>) {
    if (!hasDraggedFiles(event)) {
      return;
    }

    event.preventDefault();
    if (!disabled) {
      setDragActive(true);
    }
  }

  function handleDragLeave(event: DragEvent<HTMLFormElement>) {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setDragActive(false);
    }
  }

  function handleDrop(event: DragEvent<HTMLFormElement>) {
    if (!hasDraggedFiles(event)) {
      return;
    }

    event.preventDefault();
    setDragActive(false);
    if (disabled) {
      return;
    }

    const files = Array.from(event.dataTransfer.files);
    if (!files.length) {
      return;
    }

    onUploadFiles(files);
  }

  function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!files.length || disabled) {
      return;
    }

    onUploadFiles(files);
  }

  return (
    <form
      className="shrink-0 border-t bg-card p-3 sm:p-4"
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onSubmit={onSubmit}
    >
      <div className="mx-auto flex w-full max-w-4xl items-end gap-2 sm:gap-3">
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
          <div
            className={cn(
              "rounded-md border bg-card transition-colors focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background",
              dragActive && "border-ring bg-accent/40",
              disabled && "opacity-50",
            )}
          >
            {uploadAttachments.length || uploadPending || uploadError ? (
              <div className="flex min-h-8 flex-wrap items-center gap-1.5 px-3 pt-2">
                {uploadAttachments.map((attachment) => (
                  <span className="file-mention-pill pr-1" key={attachment.id}>
                    <span className="truncate">{attachment.label}</span>
                    <Button
                      className="ml-1 size-5 rounded-full"
                      disabled={uploadPending}
                      size="icon"
                      type="button"
                      variant="ghost"
                      onClick={() => onUploadAttachmentRemove(attachment.id)}
                    >
                      <X data-icon="inline-start" />
                      <span className="sr-only">Remove file</span>
                    </Button>
                  </span>
                ))}
                {uploadPending ? (
                  <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Loader2 className="animate-spin" data-icon="inline-start" />
                    Uploading
                  </span>
                ) : null}
                {uploadError ? (
                  <span className="text-xs text-destructive">{uploadError}</span>
                ) : null}
              </div>
            ) : null}
            <div className="flex min-h-10 items-end">
              <input
                className="hidden"
                multiple
                ref={fileInputRef}
                type="file"
                onChange={handleFileInputChange}
              />
              <Textarea
                className="max-h-32 min-h-10 resize-none border-0 bg-transparent px-3 py-2 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
                disabled={disabled}
                onChange={(event) => {
                  onMessageChange(event.target.value);
                  onCursorSync(event.currentTarget);
                }}
                onClick={(event) => onCursorSync(event.currentTarget)}
                onKeyDown={handleKeyDown}
                onKeyUp={(event) => onCursorSync(event.currentTarget)}
                placeholder="메시지를 입력하세요"
                ref={textareaRef}
                rows={1}
                value={message}
              />
              <Button
                className="mb-1 mr-1 size-8 shrink-0 text-muted-foreground"
                disabled={disabled}
                size="icon"
                type="button"
                variant="ghost"
                onClick={() => fileInputRef.current?.click()}
              >
                {uploadPending ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Paperclip />
                )}
                <span className="sr-only">Attach files</span>
              </Button>
            </div>
          </div>
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
          className="h-10 shrink-0 px-4 sm:px-5"
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

function hasDraggedFiles(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.types).includes("Files");
}

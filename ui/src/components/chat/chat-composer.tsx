import {
  forwardRef,
  lazy,
  memo,
  Suspense,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import type {
  ChangeEvent,
  DragEvent,
  FormEvent,
  KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { ArrowUp, Loader2, Paperclip } from "lucide-react";

import {
  composerPayloadFromText,
  type ComposerEditorHandle,
  type ComposerEditorRuntimeHandle,
  type ComposerSubmitPayload,
} from "@/lib/composer-editor";
import {
  fileMentionAttachmentFromDragPayload,
  readFileMentionDragPayload,
  type FileMentionAttachment,
} from "@/lib/file-mentions";
import {
  loadChatComposerEditorComponent,
  preloadChatComposerEditor,
} from "@/components/chat/chat-composer-loader";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type { ComposerEditorHandle, ComposerSubmitPayload };

type ChatComposerProps = {
  disabled: boolean;
  sessionUuid: string;
  uploadError: string | null;
  uploadPending: boolean;
  userId: string;
  onUploadFiles(files: File[]): void;
  onSubmit(event: FormEvent<HTMLFormElement>, payload: ComposerSubmitPayload): Promise<boolean>;
};

const LazyChatComposerEditor = lazy(loadChatComposerEditorComponent);

export const ChatComposer = memo(
  forwardRef<ComposerEditorHandle, ChatComposerProps>(function ChatComposer(
    {
      disabled,
      sessionUuid,
      uploadError,
      uploadPending,
      userId,
      onUploadFiles,
      onSubmit,
    },
    ref,
  ) {
    const [dragActive, setDragActive] = useState(false);
    const [editorRequested, setEditorRequested] = useState(false);
    const [editorEmpty, setEditorEmpty] = useState(true);
    const [fallbackText, setFallbackText] = useState("");
    const [pendingAttachments, setPendingAttachments] = useState<
      FileMentionAttachment[]
    >([]);
    const editorRef = useRef<ComposerEditorRuntimeHandle | null>(null);
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const formRef = useRef<HTMLFormElement | null>(null);
    const textareaRef = useRef<HTMLTextAreaElement | null>(null);

    const requestEditor = useCallback(() => {
      setEditorRequested(true);
      preloadChatComposerEditor();
    }, []);

    useEffect(() => {
      const idleWindow = window as Window & {
        cancelIdleCallback?: (handle: number) => void;
        requestIdleCallback?: (
          callback: () => void,
          options?: { timeout: number },
        ) => number;
      };

      if (idleWindow.requestIdleCallback) {
        const handle = idleWindow.requestIdleCallback(requestEditor, {
          timeout: 1500,
        });
        return () => idleWindow.cancelIdleCallback?.(handle);
      }

      const timeout = window.setTimeout(requestEditor, 600);
      return () => window.clearTimeout(timeout);
    }, [requestEditor]);

    useImperativeHandle(
      ref,
      () => ({
        clear() {
          setFallbackText("");
          setEditorEmpty(true);
          setPendingAttachments([]);
          editorRef.current?.clear();
        },
        focus() {
          requestEditor();
          if (editorRef.current) {
            editorRef.current.focus();
            return;
          }
          textareaRef.current?.focus();
        },
        insertFileMentions(attachments) {
          if (!attachments.length) {
            return;
          }

          requestEditor();
          if (editorRef.current) {
            editorRef.current.insertFileMentions(attachments);
            return;
          }
          setPendingAttachments((current) => [...current, ...attachments]);
        },
      }),
      [requestEditor],
    );

    const setEditorRef = useCallback(
      (handle: ComposerEditorRuntimeHandle | null) => {
        editorRef.current = handle;
      },
      [],
    );

    const clearPendingAttachments = useCallback(() => {
      setPendingAttachments([]);
    }, []);

    function handleDragOver(event: DragEvent<HTMLFormElement>) {
      if (!hasDraggedFiles(event) && !hasDraggedFileMention(event)) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      if (!disabled) {
        setDragActive(true);
      }
    }

    function handleDragLeave(event: DragEvent<HTMLFormElement>) {
      event.stopPropagation();
      if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
        setDragActive(false);
      }
    }

    function handleDrop(event: DragEvent<HTMLFormElement>) {
      const fileMentionPayload = readFileMentionDragPayload(event.dataTransfer);
      if (fileMentionPayload) {
        event.preventDefault();
        event.stopPropagation();
        setDragActive(false);
        if (!disabled) {
          requestEditor();
          const attachment =
            fileMentionAttachmentFromDragPayload(fileMentionPayload);
          if (editorRef.current) {
            editorRef.current.insertFileMentions([attachment]);
          } else {
            setPendingAttachments((current) => [...current, attachment]);
          }
        }
        return;
      }

      if (!hasDraggedFiles(event)) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      setDragActive(false);
      if (disabled) {
        return;
      }

      requestEditor();
      const files = Array.from(event.dataTransfer.files);
      if (files.length) {
        onUploadFiles(files);
      }
    }

    function handleFallbackKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
      if (event.key !== "Enter" || event.shiftKey || disabled || isComposing(event)) {
        return;
      }

      event.preventDefault();
      formRef.current?.requestSubmit();
    }

    function handleFileInputChange(event: ChangeEvent<HTMLInputElement>) {
      const files = Array.from(event.target.files ?? []);
      event.target.value = "";
      if (!files.length || disabled) {
        return;
      }

      requestEditor();
      onUploadFiles(files);
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
      event.preventDefault();
      if (pendingAttachments.length) {
        requestEditor();
        return;
      }

      const payload =
        editorRef.current?.getPayload() ?? composerPayloadFromText(fallbackText);
      const submitted = await onSubmit(event, payload);
      if (submitted) {
        setFallbackText("");
        setEditorEmpty(true);
        setPendingAttachments([]);
        editorRef.current?.clear();
      }
    }

    const fallbackEditor = (
      <textarea
        aria-label="Message"
        className="max-h-40 min-h-24 w-full resize-none border-0 bg-transparent px-7 pb-2 pt-7 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-0"
        disabled={disabled}
        placeholder="무엇을 도와드릴까요?"
        ref={textareaRef}
        rows={1}
        value={fallbackText}
        onChange={(event) => setFallbackText(event.target.value)}
        onFocus={requestEditor}
        onKeyDown={handleFallbackKeyDown}
        onPointerEnter={requestEditor}
      />
    );
    const submitDisabled = disabled || pendingAttachments.length > 0;
    const hasComposerContent =
      pendingAttachments.length > 0 ||
      fallbackText.trim().length > 0 ||
      !editorEmpty;

    return (
      <form
        className="shrink-0 bg-background px-3 pb-4 pt-2 sm:px-4 sm:pb-5"
        ref={formRef}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onPointerEnter={requestEditor}
        onSubmit={handleSubmit}
      >
        <div
          className={cn(
            "mx-auto flex w-full max-w-4xl flex-col rounded-[28px] border bg-card shadow-[0_8px_28px_rgba(31,35,32,0.06)] transition-colors focus-within:border-ring",
            dragActive && "border-ring bg-accent/30",
            disabled && "opacity-50",
          )}
        >
          <input
            className="hidden"
            multiple
            ref={fileInputRef}
            type="file"
            onChange={handleFileInputChange}
          />
          <div className="composer-editor relative min-h-24 min-w-0">
            {editorRequested ? (
              <Suspense fallback={fallbackEditor}>
                <LazyChatComposerEditor
                  disabled={disabled}
                  initialText={fallbackText}
                  pendingAttachments={pendingAttachments}
                  ref={setEditorRef}
                  sessionUuid={sessionUuid}
                  userId={userId}
                  onEmptyChange={setEditorEmpty}
                  onPendingAttachmentsFlushed={clearPendingAttachments}
                  onSubmitRequest={() => formRef.current?.requestSubmit()}
                />
              </Suspense>
            ) : (
              fallbackEditor
            )}
          </div>
          <div className="flex min-h-14 items-center gap-3 px-5 pb-4">
            <Button
              className="size-10 shrink-0 text-muted-foreground hover:text-foreground"
              disabled={disabled}
              size="icon"
              type="button"
              variant="ghost"
              onClick={() => {
                requestEditor();
                fileInputRef.current?.click();
              }}
            >
              {uploadPending ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Paperclip />
              )}
              <span className="sr-only">Attach files</span>
            </Button>
            <div className="min-w-0 flex-1">
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
            <Button
              className={cn(
                "size-9 shrink-0 rounded-full text-background transition-colors disabled:bg-muted disabled:text-muted-foreground",
                hasComposerContent
                  ? "bg-[#2563eb] hover:bg-[#1d4ed8]"
                  : "bg-foreground/50 hover:bg-foreground/65",
              )}
              disabled={submitDisabled}
              size="icon"
              type="submit"
            >
              {disabled ? (
                <Loader2 className="animate-spin" />
              ) : (
                <ArrowUp />
              )}
              <span className="sr-only">Send</span>
            </Button>
          </div>
        </div>
      </form>
    );
  }),
);

function isComposing(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
  return event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229;
}

function hasDraggedFiles(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.types).includes("Files");
}

function hasDraggedFileMention(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.types).includes(
    "application/x-minimal-agent-file",
  );
}

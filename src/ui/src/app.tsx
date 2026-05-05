import {
  Bot,
  FileText,
  Loader2,
  PanelRightOpen,
  Plus,
  Send,
  Trash2,
} from "lucide-react";
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";

import {
  createChatStream,
  getFilePreview,
  listFiles,
  searchFiles,
  submitHitlDecision,
  type ChatMessage,
  type FsListItem,
  type FsPreviewResponse,
  type HitlDecision,
  type HitlRequest,
  uploadFiles,
} from "@/lib/api";
import {
  actionToDraft,
  type HitlDraft,
  type HitlMode,
  mergeDraftArgs,
} from "@/components/hitl/approval-model";
import { MessageCard, type UiMessage } from "@/components/chat/message-card";
import { FileDrawer } from "@/components/workspace/file-drawer";
import {
  findActiveFileMention,
  replaceFileMention,
} from "@/lib/file-mentions";
import { openChatEventSource, type AgentUiEvent } from "@/lib/stream";
import { cn } from "@/lib/utils";
import {
  createSession,
  deleteSession,
  getSessionHistory,
  getSessions,
  saveSessionHistory,
  touchSession,
  useSessionStore,
} from "@/store/session-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const FilePreviewSheet = lazy(() =>
  import("@/components/preview/file-preview-sheet").then((module) => ({
    default: module.FilePreviewSheet,
  })),
);
const HitlApprovalDialog = lazy(() =>
  import("@/components/hitl/approval-dialog").then((module) => ({
    default: module.HitlApprovalDialog,
  })),
);

type MentionStatus = "idle" | "loading" | "ready" | "error";

const PREVIEW_EXTENSIONS = new Set([
  "pdf",
  "py",
  "js",
  "jsx",
  "mjs",
  "cjs",
  "ts",
  "tsx",
  "sql",
  "html",
  "htm",
  "css",
  "java",
  "go",
  "sh",
  "bash",
  "zsh",
  "json",
  "docx",
  "pptx",
  "xlsx",
  "hwpx",
  "md",
  "markdown",
  "txt",
]);

function createId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function isPreviewSupported(filename: string) {
  const extension = filename.split(".").pop()?.toLowerCase() ?? "";
  return PREVIEW_EXTENSIONS.has(extension);
}

export function App() {
  return (
    <TooltipProvider>
      <MinimalAgentShell />
    </TooltipProvider>
  );
}

function MinimalAgentShell() {
  const {
    userId,
    sessionUuid,
    fileDrawerOpen,
    setUserId,
    setSessionUuid,
    setFileDrawerOpen,
  } = useSessionStore();
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("Idle");
  const [uiMessages, setUiMessages] = useState<UiMessage[]>(() =>
    getSessionHistory(userId, sessionUuid).map((item) => ({
      ...item,
      id: createId(),
    })),
  );
  const [files, setFiles] = useState<FsListItem[]>([]);
  const [fileStatus, setFileStatus] = useState("Ready");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [activePreviewFile, setActivePreviewFile] = useState<FsListItem | null>(null);
  const [activePreview, setActivePreview] = useState<FsPreviewResponse | null>(null);
  const [previewStatus, setPreviewStatus] = useState("Ready");
  const [cursorIndex, setCursorIndex] = useState(0);
  const [mentionMatches, setMentionMatches] = useState<FsListItem[]>([]);
  const [mentionStatus, setMentionStatus] = useState<MentionStatus>("idle");
  const [mentionIndex, setMentionIndex] = useState(0);
  const [activeStreamId, setActiveStreamId] = useState<string | null>(null);
  const [pendingHitl, setPendingHitl] = useState<HitlRequest | null>(null);
  const [hitlMode, setHitlMode] = useState<HitlMode>("review");
  const [hitlDrafts, setHitlDrafts] = useState<HitlDraft[]>([]);
  const [hitlRejectMessage, setHitlRejectMessage] = useState("");
  const [hitlStatus, setHitlStatus] = useState<string | null>(null);
  const [hitlSubmitting, setHitlSubmitting] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const sessions = useMemo(() => getSessions(userId), [userId, sessionUuid]);
  const currentSession =
    sessions.find((session) => session.uuid === sessionUuid) ?? sessions[0];
  const activeMention = useMemo(
    () => findActiveFileMention(message, cursorIndex),
    [message, cursorIndex],
  );
  const mentionQuery = activeMention?.query.trim() ?? "";
  const canSearchMention = mentionQuery.length > 0 && !mentionQuery.includes("/");
  const chatBlocked =
    status === "Streaming" ||
    status === "Approval required" ||
    status === "Resuming";

  useEffect(() => {
    if (!activeMention || !canSearchMention) {
      setMentionMatches([]);
      setMentionStatus("idle");
      setMentionIndex(0);
      return;
    }

    let ignore = false;
    setMentionStatus("loading");
    setMentionIndex(0);

    void searchFiles({
      userId,
      sessionUuid,
      query: mentionQuery,
      limit: 10,
    })
      .then((response) => {
        if (ignore) {
          return;
        }
        setMentionMatches(response.matches);
        setMentionStatus("ready");
      })
      .catch(() => {
        if (ignore) {
          return;
        }
        setMentionMatches([]);
        setMentionStatus("error");
      });

    return () => {
      ignore = true;
    };
  }, [activeMention, canSearchMention, mentionQuery, sessionUuid, userId]);

  function closeStream() {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }

  function clearHitlState() {
    setActiveStreamId(null);
    setPendingHitl(null);
    setHitlMode("review");
    setHitlDrafts([]);
    setHitlRejectMessage("");
    setHitlStatus(null);
    setHitlSubmitting(false);
  }

  function switchSession(nextUuid: string) {
    closeStream();
    closeMentionPanel();
    clearHitlState();
    setSessionUuid(nextUuid);
    setUiMessages(
      getSessionHistory(userId, nextUuid).map((item) => ({
        ...item,
        id: createId(),
      })),
    );
    setStatus("Idle");
  }

  function startSession() {
    const session = createSession(userId);
    switchSession(session.uuid);
  }

  function syncComposerCursor(element: HTMLTextAreaElement) {
    setCursorIndex(element.selectionStart);
  }

  function closeMentionPanel() {
    setMentionMatches([]);
    setMentionStatus("idle");
    setMentionIndex(0);
  }

  function selectMention(file: FsListItem) {
    if (!activeMention) {
      return;
    }

    const next = replaceFileMention(message, activeMention, file.path);
    setMessage(next.value);
    closeMentionPanel();

    requestAnimationFrame(() => {
      textareaRef.current?.focus();
      textareaRef.current?.setSelectionRange(next.cursorIndex, next.cursorIndex);
      setCursorIndex(next.cursorIndex);
    });
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (!activeMention || !canSearchMention || mentionStatus === "idle") {
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      closeMentionPanel();
      return;
    }

    if (mentionMatches.length === 0) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setMentionIndex((current) => (current + 1) % mentionMatches.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setMentionIndex(
        (current) => (current - 1 + mentionMatches.length) % mentionMatches.length,
      );
      return;
    }

    if (event.key === "Enter" || event.key === "Tab") {
      event.preventDefault();
      selectMention(mentionMatches[mentionIndex]);
    }
  }

  function removeSession(uuid: string) {
    const remaining = deleteSession(userId, uuid);
    if (uuid !== sessionUuid) {
      return;
    }
    const next = remaining[0] ?? createSession(userId);
    switchSession(next.uuid);
  }

  function appendAssistantText(text: string) {
    setUiMessages((current) => {
      const next = [...current];
      const last = next.at(-1);

      if (last?.role === "assistant" && last.kind === "normal") {
        next[next.length - 1] = {
          ...last,
          content: `${last.content}${text}`,
        };
        return next;
      }

      return [
        ...next,
        { id: createId(), role: "assistant", content: text, kind: "normal" },
      ];
    });
  }

  function appendEvent(event: AgentUiEvent) {
    if (event.kind === "assistant_delta" && event.text) {
      appendAssistantText(event.text);
      return;
    }

    if (event.kind === "think_delta" && event.text) {
      const text = event.text;
      setUiMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: text,
          kind: "reasoning",
        },
      ]);
      return;
    }

    if (event.kind === "activity") {
      const activityId = event.id ? `activity:${event.id}` : createId();
      setUiMessages((current) => {
        const nextMessage: UiMessage = {
          id: activityId,
          role: "assistant",
          content: event.message || event.label || event.name || "Agent activity",
          kind: "activity",
          activity: event,
        };
        const existingIndex = current.findIndex((item) => item.id === activityId);
        if (existingIndex === -1) {
          return [...current, nextMessage];
        }
        const next = [...current];
        next[existingIndex] = nextMessage;
        return next;
      });
    }
  }

  async function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = message.trim();

    if (!content || chatBlocked) {
      return;
    }

    closeStream();
    closeMentionPanel();
    clearHitlState();
    setMessage("");
    setStatus("Streaming");

    const history = getSessionHistory(userId, sessionUuid);
    const nextHistory: ChatMessage[] = [...history, { role: "user", content }];

    setUiMessages((current) => [
      ...current,
      { id: createId(), role: "user", content },
    ]);

    try {
      const streamId = await createChatStream({
        userId,
        sessionUuid,
        message: content,
        chatHistory: history,
      });
      setActiveStreamId(streamId);

      let assistantText = "";
      const source = openChatEventSource(streamId, {
        onEvent(uiEvent) {
          if (uiEvent.kind === "assistant_delta" && uiEvent.text) {
            assistantText += uiEvent.text;
          }
          appendEvent(uiEvent);
        },
        onHitlRequest(hitlRequest) {
          setPendingHitl(hitlRequest);
          setHitlMode("review");
          setHitlDrafts(hitlRequest.actions.map(actionToDraft));
          setHitlRejectMessage("");
          setHitlStatus(null);
          setStatus("Approval required");
        },
        onHitlResumed() {
          setPendingHitl(null);
          setHitlMode("review");
          setHitlDrafts([]);
          setHitlRejectMessage("");
          setHitlStatus(null);
          setStatus("Streaming");
        },
        onDone() {
          const completedHistory = assistantText
            ? [
                ...nextHistory,
                { role: "assistant" as const, content: assistantText },
              ]
            : nextHistory;
          saveSessionHistory(userId, sessionUuid, completedHistory);
          touchSession(userId, sessionUuid, content);
          setStatus("Idle");
          clearHitlState();
          closeStream();
        },
        onError(errorMessage) {
          setUiMessages((current) => [
            ...current,
            {
              id: createId(),
              role: "assistant",
              content: errorMessage,
              kind: "error",
            },
          ]);
          setStatus("Error");
          clearHitlState();
          closeStream();
        },
      });

      eventSourceRef.current = source;
    } catch (error) {
      setUiMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: error instanceof Error ? error.message : "Request failed.",
          kind: "error",
        },
      ]);
      setStatus("Error");
      clearHitlState();
    }
  }

  async function submitApproval(decisionType: HitlDecision["type"]) {
    if (!activeStreamId || !pendingHitl) {
      return;
    }

    let decisions: HitlDecision[];
    try {
      if (decisionType === "approve") {
        decisions = pendingHitl.actions.map(() => ({ type: "approve" }));
      } else if (decisionType === "reject") {
        decisions = pendingHitl.actions.map(() => ({
          type: "reject",
          message: hitlRejectMessage.trim() || "Rejected by user.",
        }));
      } else {
        decisions = pendingHitl.actions.map((action, index) => {
          const draft = hitlDrafts[index] ?? actionToDraft(action);
          return {
            type: "edit",
            edited_action: {
              name: action.name,
              args: mergeDraftArgs(action, draft),
            },
          };
        });
      }
    } catch (error) {
      setHitlStatus(error instanceof Error ? error.message : "Invalid approval input.");
      return;
    }

    setHitlSubmitting(true);
    setHitlStatus("승인 결정을 제출하는 중입니다...");
    try {
      await submitHitlDecision({ streamId: activeStreamId, decisions });
      setStatus("Resuming");
      setHitlStatus("승인 결정이 제출되었습니다.");
    } catch (error) {
      setHitlStatus(error instanceof Error ? error.message : "Approval failed.");
      setHitlSubmitting(false);
    }
  }

  async function refreshFiles() {
    setFileStatus("Loading");
    try {
      const response = await listFiles({ userId, sessionUuid });
      setFiles(response.files);
      setFileStatus("Ready");
    } catch (error) {
      setFiles([]);
      setFileStatus(error instanceof Error ? error.message : "File list failed.");
    }
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem("files");
    if (!(input instanceof HTMLInputElement) || !input.files?.length) {
      return;
    }

    setFileStatus("Uploading");
    try {
      await uploadFiles({ userId, sessionUuid, files: Array.from(input.files) });
      input.value = "";
      await refreshFiles();
    } catch (error) {
      setFileStatus(error instanceof Error ? error.message : "Upload failed.");
    }
  }

  async function openPreview(file: FsListItem) {
    if (file.type !== "file" || !isPreviewSupported(file.name)) {
      return;
    }
    setActivePreviewFile(file);
    setPreviewOpen(true);
    setPreviewStatus("Loading");
    setActivePreview(null);
    try {
      const preview = await getFilePreview({
        userId,
        sessionUuid,
        path: file.path,
      });
      setActivePreview(preview);
      setPreviewStatus("Ready");
    } catch (error) {
      setPreviewStatus(error instanceof Error ? error.message : "Preview failed.");
    }
  }

  async function refreshPreview() {
    if (!activePreviewFile) {
      return;
    }
    await openPreview(activePreviewFile);
  }

  return (
    <main className="flex min-h-svh overflow-hidden bg-background text-foreground">
      <aside className="hidden w-72 shrink-0 border-r bg-card px-4 py-4 lg:flex lg:flex-col">
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-md border bg-background text-muted-foreground">
            <Bot data-icon="inline-start" />
          </div>
          <div>
            <h1 className="text-base font-semibold">MinimalAgent</h1>
            <p className="text-xs text-muted-foreground">Local agent console</p>
          </div>
        </div>

        <div className="mt-6 flex flex-col gap-2">
          <label
            className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground"
            htmlFor="user-id"
          >
            User ID
          </label>
          <Input
            id="user-id"
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
          />
        </div>

        <Separator className="my-5" />

        <div className="flex items-center justify-between">
          <h2 className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Sessions
          </h2>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button size="icon" variant="ghost" onClick={startSession}>
                <Plus data-icon="inline-start" />
                <span className="sr-only">New session</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>New session</TooltipContent>
          </Tooltip>
        </div>

        <ScrollArea className="mt-2 flex-1">
          <div className="flex flex-col gap-1 pr-2">
            {sessions.map((session) => (
              <div key={session.uuid} className="group relative">
                <Button
                  className="w-full min-w-0 justify-start px-3 pr-11"
                  variant={session.uuid === sessionUuid ? "secondary" : "ghost"}
                  onClick={() => switchSession(session.uuid)}
                >
                  <span className="truncate">{session.title}</span>
                </Button>
                <Button
                  className="pointer-events-none absolute right-1 top-1/2 -translate-y-1/2 text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-focus-within:pointer-events-auto group-focus-within:opacity-100 group-hover:pointer-events-auto group-hover:opacity-100"
                  size="icon"
                  variant="ghost"
                  onClick={(event) => {
                    event.stopPropagation();
                    removeSession(session.uuid);
                  }}
                >
                  <Trash2 data-icon="inline-start" />
                  <span className="sr-only">Delete session</span>
                </Button>
              </div>
            ))}
          </div>
        </ScrollArea>

        <Badge className="mt-4 w-fit bg-background text-muted-foreground" variant="outline">
          {status}
        </Badge>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="border-b bg-background px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold">Chat</p>
                <Badge className="bg-card text-muted-foreground" variant="outline">
                  {status}
                </Badge>
              </div>
              <p className="truncate font-mono text-[11px] text-muted-foreground">
                {currentSession?.title ?? sessionUuid}
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => {
                setFileDrawerOpen(true);
                void refreshFiles();
              }}
            >
              <PanelRightOpen data-icon="inline-start" />
              Files
            </Button>
          </div>

          <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto] lg:hidden">
            <label className="sr-only" htmlFor="mobile-user-id">
              User ID
            </label>
            <Input
              className="h-8 text-xs"
              id="mobile-user-id"
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
            />
            <label className="sr-only" htmlFor="mobile-session">
              Session
            </label>
            <select
              className="h-8 min-w-0 rounded-md border bg-card px-3 text-xs text-foreground shadow-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              id="mobile-session"
              value={sessionUuid}
              onChange={(event) => switchSession(event.target.value)}
            >
              {sessions.map((session) => (
                <option key={session.uuid} value={session.uuid}>
                  {session.title}
                </option>
              ))}
            </select>
            <Button className="h-8" size="sm" variant="secondary" onClick={startSession}>
              <Plus data-icon="inline-start" />
              New
            </Button>
          </div>
        </header>

        <ScrollArea className="flex-1">
          <div className="mx-auto flex w-full max-w-4xl flex-col gap-3 px-4 py-5 sm:py-6">
            {uiMessages.length === 0 ? (
              <Card className="border-dashed bg-card/80">
                <CardHeader>
                  <CardTitle>Start a session</CardTitle>
                  <CardDescription>
                    Send a message or upload files to work in the local workspace.
                  </CardDescription>
                </CardHeader>
              </Card>
            ) : (
              uiMessages.map((item) => <MessageCard key={item.id} item={item} />)
            )}
          </div>
        </ScrollArea>

        <form className="border-t bg-card p-3 sm:p-4" onSubmit={submitMessage}>
          <div className="mx-auto flex w-full max-w-4xl flex-col gap-2 sm:flex-row sm:gap-3">
            <div className="relative min-w-0 flex-1">
              {activeMention && canSearchMention && mentionStatus !== "idle" ? (
                <div className="absolute bottom-full left-0 right-0 mb-2 rounded-lg border bg-card p-1 shadow-[0_8px_24px_rgba(31,35,32,0.08)]">
                  {mentionStatus === "loading" ? (
                    <div className="px-3 py-2 text-sm text-muted-foreground">
                      Searching files...
                    </div>
                  ) : null}
                  {mentionStatus === "error" ? (
                    <div className="px-3 py-2 text-sm text-destructive">
                      File search failed.
                    </div>
                  ) : null}
                  {mentionStatus === "ready" && mentionMatches.length === 0 ? (
                    <div className="px-3 py-2 text-sm text-muted-foreground">
                      No matching files.
                    </div>
                  ) : null}
                  {mentionMatches.length > 0 ? (
                    <div aria-label="File mention suggestions" role="listbox">
                      {mentionMatches.map((file, index) => (
                        <button
                          aria-selected={index === mentionIndex}
                          className={cn(
                            "flex w-full min-w-0 items-center gap-3 rounded-md px-3 py-2 text-left text-sm",
                            index === mentionIndex
                              ? "bg-secondary"
                              : "hover:bg-secondary",
                          )}
                          key={file.path}
                          onMouseDown={(event) => {
                            event.preventDefault();
                            selectMention(file);
                          }}
                          role="option"
                          type="button"
                        >
                          <FileText
                            className="text-muted-foreground"
                            data-icon="inline-start"
                          />
                          <span className="min-w-0">
                            <span className="block truncate font-medium">
                              {file.name}
                            </span>
                            <span className="block truncate font-mono text-[11px] text-muted-foreground">
                              {file.path}
                            </span>
                          </span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
              <Textarea
                className="min-h-20 resize-none"
                onChange={(event) => {
                  setMessage(event.target.value);
                  syncComposerCursor(event.currentTarget);
                }}
                onClick={(event) => syncComposerCursor(event.currentTarget)}
                onKeyDown={handleComposerKeyDown}
                onKeyUp={(event) => syncComposerCursor(event.currentTarget)}
                placeholder="메시지를 입력하세요"
                ref={textareaRef}
                value={message}
              />
            </div>
            <Button
              className="h-10 self-stretch px-5 sm:h-20"
              disabled={chatBlocked}
              type="submit"
            >
              {chatBlocked ? (
                <Loader2 className="animate-spin" data-icon="inline-start" />
              ) : (
                <Send data-icon="inline-start" />
              )}
              Send
            </Button>
          </div>
        </form>
      </section>

      <FileDrawer
        files={files}
        isPreviewSupported={isPreviewSupported}
        open={fileDrawerOpen}
        status={fileStatus}
        onOpenChange={setFileDrawerOpen}
        onPreview={(file) => {
          void openPreview(file);
        }}
        onRefresh={() => {
          void refreshFiles();
        }}
        onUpload={submitUpload}
      />
      {previewOpen ? (
        <Suspense fallback={null}>
          <FilePreviewSheet
            open={previewOpen}
            preview={activePreview}
            status={previewStatus}
            onOpenChange={setPreviewOpen}
            onRefresh={() => {
              void refreshPreview();
            }}
          />
        </Suspense>
      ) : null}
      {pendingHitl ? (
        <Suspense fallback={null}>
          <HitlApprovalDialog
            drafts={hitlDrafts}
            mode={hitlMode}
            request={pendingHitl}
            rejectMessage={hitlRejectMessage}
            status={hitlStatus}
            submitting={hitlSubmitting}
            onApprove={() => {
              void submitApproval("approve");
            }}
            onDraftChange={(index, field, value) => {
              setHitlDrafts((current) => {
                const next = [...current];
                next[index] = {
                  ...(next[index] ?? {
                    path: "",
                    content: "",
                    instruction: "",
                  }),
                  [field]: value,
                };
                return next;
              });
            }}
            onModeChange={setHitlMode}
            onReject={() => {
              void submitApproval("reject");
            }}
            onRejectMessageChange={setHitlRejectMessage}
            onSubmitEdit={() => {
              void submitApproval("edit");
            }}
          />
        </Suspense>
      ) : null}
    </main>
  );
}

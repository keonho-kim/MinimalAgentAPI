import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Bot,
  FileText,
  Loader2,
  PanelRightOpen,
  Plus,
  RefreshCw,
  Send,
  Trash2,
  Upload,
} from "lucide-react";
import { lazy, Suspense, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";

import {
  createChatStream,
  listFiles,
  type ChatMessage,
  type FsListItem,
  uploadFiles,
} from "@/lib/api";
import { openChatEventSource, type AgentUiEvent } from "@/lib/stream";
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
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const queryClient = new QueryClient();
const MessageRenderer = lazy(() =>
  import("@/components/message-renderer").then((module) => ({
    default: module.MessageRenderer,
  })),
);

type UiMessage = ChatMessage & {
  id: string;
  kind?: "normal" | "reasoning" | "activity" | "error";
};

function createId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <MinimalAgentShell />
      </TooltipProvider>
    </QueryClientProvider>
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
  const eventSourceRef = useRef<EventSource | null>(null);
  const sessions = useMemo(() => getSessions(userId), [userId, sessionUuid]);

  function closeStream() {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }

  function switchSession(nextUuid: string) {
    closeStream();
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

    if (!content || status === "Streaming") {
      return;
    }

    closeStream();
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

      let assistantText = "";
      const source = openChatEventSource(streamId, {
        onEvent(uiEvent) {
          if (uiEvent.kind === "assistant_delta" && uiEvent.text) {
            assistantText += uiEvent.text;
          }
          appendEvent(uiEvent);
        },
        onDone() {
          const completedHistory = assistantText
            ? [...nextHistory, { role: "assistant" as const, content: assistantText }]
            : nextHistory;
          saveSessionHistory(userId, sessionUuid, completedHistory);
          touchSession(userId, sessionUuid, content);
          setStatus("Idle");
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

  return (
    <main className="flex min-h-svh bg-background text-foreground">
      <aside className="hidden w-72 shrink-0 border-r bg-card px-5 py-5 lg:flex lg:flex-col">
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-md border bg-background">
            <Bot data-icon="inline-start" />
          </div>
          <div>
            <h1 className="text-base font-semibold">MinimalAgent</h1>
            <p className="text-xs text-muted-foreground">SSE Console</p>
          </div>
        </div>

        <div className="mt-6 flex flex-col gap-2">
          <label className="text-xs font-medium text-muted-foreground" htmlFor="user-id">
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
          <h2 className="text-sm font-medium">Sessions</h2>
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
              <div key={session.uuid} className="flex items-center gap-1">
                <Button
                  className="min-w-0 flex-1 justify-start"
                  variant={session.uuid === sessionUuid ? "secondary" : "ghost"}
                  onClick={() => switchSession(session.uuid)}
                >
                  <span className="truncate">{session.title}</span>
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => removeSession(session.uuid)}
                >
                  <Trash2 data-icon="inline-start" />
                  <span className="sr-only">Delete session</span>
                </Button>
              </div>
            ))}
          </div>
        </ScrollArea>

        <Badge className="mt-4 w-fit" variant="outline">
          {status}
        </Badge>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b bg-background px-4">
          <div>
            <p className="text-sm font-medium">Chat</p>
            <p className="text-xs text-muted-foreground">{sessionUuid}</p>
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
        </header>

        <ScrollArea className="flex-1">
          <div className="mx-auto flex w-full max-w-4xl flex-col gap-3 px-4 py-6">
            {uiMessages.length === 0 ? (
              <Card>
                <CardHeader>
                  <CardTitle>Start a session</CardTitle>
                  <CardDescription>
                    Send a message or upload files to work inside the local agent
                    workspace.
                  </CardDescription>
                </CardHeader>
              </Card>
            ) : (
              uiMessages.map((item) => <MessageCard key={item.id} item={item} />)
            )}
          </div>
        </ScrollArea>

        <form className="border-t bg-card p-4" onSubmit={submitMessage}>
          <div className="mx-auto flex w-full max-w-4xl gap-3">
            <Textarea
              className="min-h-20 resize-none"
              placeholder="메시지를 입력하세요"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
            />
            <Button
              className="h-20 self-stretch px-5"
              disabled={status === "Streaming"}
              type="submit"
            >
              {status === "Streaming" ? (
                <Loader2 className="animate-spin" data-icon="inline-start" />
              ) : (
                <Send data-icon="inline-start" />
              )}
              Send
            </Button>
          </div>
        </form>
      </section>

      <Sheet open={fileDrawerOpen} onOpenChange={setFileDrawerOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Workspace Files</SheetTitle>
            <SheetDescription>{fileStatus}</SheetDescription>
          </SheetHeader>
          <form className="mt-5 flex gap-2" onSubmit={submitUpload}>
            <Input name="files" type="file" multiple />
            <Button type="submit">
              <Upload data-icon="inline-start" />
              Upload
            </Button>
          </form>
          <Button className="mt-3" variant="outline" onClick={refreshFiles}>
            <RefreshCw data-icon="inline-start" />
            Refresh
          </Button>
          <div className="mt-5 flex flex-col gap-2">
            {files.length === 0 ? (
              <p className="text-sm text-muted-foreground">No visible files.</p>
            ) : (
              files.map((file) => (
                <Card key={file.path}>
                  <CardContent className="flex items-center gap-3 p-3">
                    <FileText data-icon="inline-start" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{file.name}</p>
                      <p className="text-xs text-muted-foreground">{file.type}</p>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </SheetContent>
      </Sheet>
    </main>
  );
}

function MessageCard({ item }: { item: UiMessage }) {
  const variant =
    item.kind === "error"
      ? "border-destructive/30 bg-destructive/5"
      : item.kind === "reasoning"
        ? "bg-muted"
        : item.kind === "activity"
          ? "bg-accent"
          : item.role === "user"
            ? "ml-auto max-w-[80%] bg-primary text-primary-foreground"
            : "mr-auto max-w-[80%]";

  return (
    <Card className={variant}>
      <CardContent className="p-4">
        <Suspense
          fallback={
            <div className="message-renderer whitespace-pre-wrap">
              {item.content}
            </div>
          }
        >
          <MessageRenderer content={item.content} role={item.role} />
        </Suspense>
      </CardContent>
    </Card>
  );
}

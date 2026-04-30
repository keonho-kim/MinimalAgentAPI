export type AgentUiEvent =
  | {
      kind: "assistant_delta" | "think_delta";
      id?: string;
      parentIds?: string[];
      text?: string;
    }
  | {
      kind: "activity";
      id?: string;
      name?: string;
      label?: string;
      message?: string;
      status?: string;
      input?: unknown;
      output?: unknown;
      summary?: unknown;
    }
  | {
      kind: "raw";
      raw: unknown;
    };

export function openChatEventSource(
  streamId: string,
  handlers: {
    onEvent(event: AgentUiEvent): void;
    onDone(): void;
    onError(message: string): void;
  },
) {
  const source = new EventSource(`/chat/stream/${streamId}`);

  source.addEventListener("agent_ui", (streamEvent) => {
    handlers.onEvent(JSON.parse(streamEvent.data) as AgentUiEvent);
  });

  source.addEventListener("done", () => {
    handlers.onDone();
  });

  source.addEventListener("error", (streamEvent) => {
    const messageEvent = streamEvent as MessageEvent<string>;
    const data = messageEvent.data ? JSON.parse(messageEvent.data) : {};
    handlers.onError(data.message || "Stream connection failed.");
  });

  return source;
}

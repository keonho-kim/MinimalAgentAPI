import { apiUrl } from "@/lib/backend-url";
import type { HitlRequest } from "@/lib/api";

export type AgentUiEvent =
  | {
      kind: "assistant_delta" | "think_delta";
      id?: string;
      sourceEvent?: string;
      name?: string;
      runId?: string;
      parentIds?: string[];
      text?: string;
    }
  | {
      kind: "activity";
      type?: string;
      id?: string;
      sourceEvent?: string;
      runId?: string;
      parentIds?: string[];
      name?: string;
      label?: string;
      message?: string;
      status?: string;
      input?: unknown;
      output?: unknown;
      summary?: unknown;
    };

export function openChatEventSource(
  streamId: string,
  handlers: {
    onEvent(event: AgentUiEvent): void;
    onHitlRequest(event: HitlRequest): void;
    onHitlResumed?(event: { stream_id?: string; status?: string }): void;
    onDone(): void;
    onError(message: string): void;
  },
) {
  const source = new EventSource(apiUrl(`/chat/stream/${streamId}`));

  source.addEventListener("agent_ui", (streamEvent) => {
    handlers.onEvent(JSON.parse(streamEvent.data) as AgentUiEvent);
  });

  source.addEventListener("done", () => {
    handlers.onDone();
  });

  source.addEventListener("hitl_request", (streamEvent) => {
    handlers.onHitlRequest(JSON.parse(streamEvent.data) as HitlRequest);
  });

  source.addEventListener("hitl_resumed", (streamEvent) => {
    const data = streamEvent.data ? JSON.parse(streamEvent.data) : {};
    handlers.onHitlResumed?.(data);
  });

  source.addEventListener("error", (streamEvent) => {
    const messageEvent = streamEvent as MessageEvent<string>;
    const data = messageEvent.data ? JSON.parse(messageEvent.data) : {};
    handlers.onError(data.message || "Stream connection failed.");
  });

  return source;
}

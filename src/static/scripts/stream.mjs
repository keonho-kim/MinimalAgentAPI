import { normalizeStreamEvent } from "./events.mjs";

export function openChatEventSource(streamId, handlers) {
  const source = new EventSource(`/chat/stream/${streamId}`);

  source.addEventListener("langgraph", (streamEvent) => {
    const rawEvent = JSON.parse(streamEvent.data);
    const uiEvents = normalizeStreamEvent(rawEvent);

    for (const uiEvent of uiEvents) {
      if (uiEvent.kind === "assistant_delta") {
        handlers.onAssistantDelta(uiEvent);
      } else if (uiEvent.kind === "activity") {
        handlers.onActivity(uiEvent);
      } else if (uiEvent.kind === "raw") {
        handlers.onRawEvent(uiEvent.raw);
      }
    }
  });

  source.addEventListener("done", () => {
    handlers.onDone();
  });

  source.addEventListener("error", (streamEvent) => {
    const data = streamEvent.data ? JSON.parse(streamEvent.data) : {};
    handlers.onError(data.message || "Stream connection failed.");
  });

  return source;
}

import { normalizeStreamEvent } from "./events.mjs";

export function openChatEventSource(streamId, handlers) {
  const source = new EventSource(`/chat/stream/${streamId}`);

  function dispatchUiEvent(uiEvent) {
    if (uiEvent.kind === "assistant_delta") {
      handlers.onAssistantDelta(uiEvent);
    } else if (uiEvent.kind === "think_delta") {
      handlers.onThinkDelta?.(uiEvent);
    } else if (uiEvent.kind === "activity") {
      handlers.onActivity(uiEvent);
    } else if (uiEvent.kind === "raw") {
      handlers.onRawEvent?.(uiEvent.raw);
    }
  }

  source.addEventListener("agent_ui", (streamEvent) => {
    dispatchUiEvent(JSON.parse(streamEvent.data));
  });

  source.addEventListener("langgraph", (streamEvent) => {
    const rawEvent = JSON.parse(streamEvent.data);
    const uiEvents = normalizeStreamEvent(rawEvent);

    for (const uiEvent of uiEvents) {
      dispatchUiEvent(uiEvent);
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

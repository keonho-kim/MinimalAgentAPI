import { createChatStream } from "./api.mjs";
import { resetEventNormalization } from "./events.mjs";
import {
  appendAssistantSegment,
  appendAssistantTurn,
  elements,
  appendMessage,
  loadSession,
  randomUuid,
  renderEmptyState,
  scrollToBottom,
  setStatus,
  upsertActivity,
} from "./dom.mjs";
import { createDebouncedRenderer } from "./render.mjs";
import { closeCurrentSource, resetChatHistory, setCurrentSource, state } from "./state.mjs";
import { openChatEventSource } from "./stream.mjs";

async function submitMessage(event) {
  event.preventDefault();

  const message = elements.messageInput.value.trim();
  const userId = elements.userIdInput.value.trim();
  const sessionUuid = elements.sessionUuidInput.value.trim();

  if (!message || !userId || !sessionUuid) {
    return;
  }

  closeCurrentSource();
  resetEventNormalization();
  localStorage.setItem("minial-agent-session-uuid", sessionUuid);
  appendMessage("user", message);
  const assistantTurn = appendAssistantTurn();
  const activityCards = new Map();
  let currentRenderer = null;
  let currentSegmentText = "";

  elements.messageInput.value = "";
  elements.sendButton.disabled = true;
  setStatus("active", "Streaming");

  try {
    const streamId = await createChatStream({
      userId,
      sessionUuid,
      message,
      chatHistory: state.chatHistory,
    });
    let assistantText = "";

    function ensureRenderer() {
      if (!currentRenderer) {
        const segment = appendAssistantSegment(assistantTurn);
        currentRenderer = createDebouncedRenderer(segment);
        currentSegmentText = "";
      }

      return currentRenderer;
    }

    function flushCurrentRenderer() {
      if (currentRenderer) {
        currentRenderer.flush(currentSegmentText);
        currentRenderer = null;
        currentSegmentText = "";
      }
    }

    const source = openChatEventSource(streamId, {
      onAssistantDelta(event) {
        if (!event.text) {
          return;
        }

        assistantText += event.text;
        currentSegmentText += event.text;
        ensureRenderer().schedule(currentSegmentText);
        scrollToBottom();
      },
      onActivity(activity) {
        flushCurrentRenderer();
        upsertActivity(assistantTurn, activityCards, activity);
      },
      onDone() {
        flushCurrentRenderer();
        state.chatHistory.push({ role: "user", content: message });
        state.chatHistory.push({ role: "assistant", content: assistantText });
        closeCurrentSource();
        elements.sendButton.disabled = false;
        setStatus("idle", "Idle");
        elements.messageInput.focus();
      },
      onError(messageText) {
        appendMessage("error", messageText);
        closeCurrentSource();
        elements.sendButton.disabled = false;
        setStatus("error", "Error");
      },
    });

    setCurrentSource(source);
  } catch (error) {
    appendMessage("error", error.message);
    closeCurrentSource();
    elements.sendButton.disabled = false;
    setStatus("error", "Error");
  }
}

elements.newSessionButton.addEventListener("click", () => {
  closeCurrentSource();
  resetChatHistory();
  elements.messages.replaceChildren();
  elements.sessionUuidInput.value = randomUuid();
  localStorage.setItem("minial-agent-session-uuid", elements.sessionUuidInput.value);
  setStatus("idle", "Idle");
  renderEmptyState();
});

elements.form.addEventListener("submit", submitMessage);
loadSession();
renderEmptyState();

import { createChatStream, listFiles, uploadFiles } from "./api.mjs";
import { upsertActivity } from "./activityView.mjs";
import {
  appendAssistantSegment,
  appendAssistantTurn,
  appendMessage,
  appendThinkSegment,
  renderStoredMessages,
} from "./chatView.mjs";
import { resetEventNormalization } from "./events.mjs";
import {
  elements,
  randomUuid,
  renderEmptyState,
  renderSessionList,
  scrollToBottom,
  setActiveSessionLabel,
  setStatus,
} from "./dom.mjs";
import {
  renderFileList,
  setFileDrawerOpen,
  setFileDrawerStatus,
} from "./fileDrawerView.mjs";
import { shouldRenderActivity } from "./format.mjs";
import { createDebouncedRenderer } from "./render.mjs";
import {
  closeCurrentSource,
  createSession,
  deleteSession,
  initializeSessions,
  loadSessionHistory,
  loadSessions,
  resetChatHistory,
  saveSessionHistory,
  setActiveSessionUuid,
  setCurrentSource,
  state,
  touchSession,
} from "./state.mjs";
import { openChatEventSource } from "./stream.mjs";

function getUserId() {
  return elements.userIdInput.value.trim();
}

function getSessionUuid() {
  return elements.sessionUuidInput.value.trim();
}

function hydrateSessionUi() {
  const userId = getUserId();
  const sessionUuid = initializeSessions(userId, randomUuid);
  elements.sessionUuidInput.value = sessionUuid;
  setActiveSessionLabel(sessionUuid);
  renderSessionList(loadSessions(userId), sessionUuid);
  renderStoredMessages(state.chatHistory);
}

async function submitMessage(event) {
  event.preventDefault();

  const message = elements.messageInput.value.trim();
  const userId = getUserId();
  const sessionUuid = getSessionUuid();

  if (!message || !userId || !sessionUuid) {
    return;
  }

  closeCurrentSource();
  resetEventNormalization();
  setActiveSessionUuid(userId, sessionUuid);
  appendMessage("user", message);
  const assistantTurn = appendAssistantTurn();
  const activityCards = new Map();
  let currentRenderer = null;
  let currentSegmentText = "";
  let currentThinkRenderer = null;
  let currentThinkText = "";

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
      flushCurrentThinkRenderer();

      if (!currentRenderer) {
        const segment = appendAssistantSegment(assistantTurn);
        currentRenderer = createDebouncedRenderer(segment);
        currentSegmentText = "";
      }

      return currentRenderer;
    }

    function ensureThinkRenderer() {
      flushCurrentRenderer();

      if (!currentThinkRenderer) {
        const segment = appendThinkSegment(assistantTurn);
        currentThinkRenderer = createDebouncedRenderer(segment);
        currentThinkText = "";
      }

      return currentThinkRenderer;
    }

    function flushCurrentRenderer() {
      if (currentRenderer) {
        currentRenderer.flush(currentSegmentText);
        currentRenderer = null;
        currentSegmentText = "";
      }
    }

    function flushCurrentThinkRenderer() {
      if (currentThinkRenderer) {
        currentThinkRenderer.flush(currentThinkText);
        currentThinkRenderer = null;
        currentThinkText = "";
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
      onThinkDelta(event) {
        if (!event.text) {
          return;
        }

        currentThinkText += event.text;
        ensureThinkRenderer().schedule(currentThinkText);
        scrollToBottom();
      },
      onActivity(activity) {
        if (!shouldRenderActivity(activity)) {
          return;
        }

        flushCurrentRenderer();
        flushCurrentThinkRenderer();
        upsertActivity(assistantTurn, activityCards, activity);
      },
      onDone() {
        flushCurrentRenderer();
        flushCurrentThinkRenderer();
        state.chatHistory.push({ role: "user", content: message });
        state.chatHistory.push({ role: "assistant", content: assistantText });
        saveSessionHistory(userId, sessionUuid, state.chatHistory);
        touchSession(userId, sessionUuid, message);
        renderSessionList(loadSessions(userId), sessionUuid);
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

function switchSession(sessionUuid) {
  const userId = getUserId();
  closeCurrentSource();
  elements.sessionUuidInput.value = sessionUuid;
  setActiveSessionUuid(userId, sessionUuid);
  setActiveSessionLabel(sessionUuid);
  state.chatHistory = loadSessionHistory(userId, sessionUuid);
  renderSessionList(loadSessions(userId), sessionUuid);
  renderStoredMessages(state.chatHistory);
  setStatus("idle", "Idle");
}

function deleteSessionAndSelectNext(sessionUuid) {
  const userId = getUserId();
  const activeUuid = getSessionUuid();
  closeCurrentSource();

  const remainingSessions = deleteSession(userId, sessionUuid);

  if (sessionUuid !== activeUuid) {
    renderSessionList(remainingSessions, activeUuid);
    setStatus("idle", "Idle");
    return;
  }

  const nextSession = remainingSessions[0] || createSession(userId, randomUuid());
  elements.sessionUuidInput.value = nextSession.uuid;
  setActiveSessionUuid(userId, nextSession.uuid);
  setActiveSessionLabel(nextSession.uuid);
  state.chatHistory = loadSessionHistory(userId, nextSession.uuid);
  renderSessionList(loadSessions(userId), nextSession.uuid);
  renderStoredMessages(state.chatHistory);
  setStatus("idle", "Idle");
}

async function refreshFiles() {
  const userId = getUserId();
  const sessionUuid = getSessionUuid();

  if (!userId || !sessionUuid) {
    return;
  }

  setFileDrawerStatus("Loading");

  try {
    const response = await listFiles({ userId, sessionUuid });
    renderFileList(response.files || []);
    setFileDrawerStatus("Ready");
  } catch (error) {
    renderFileList([]);
    setFileDrawerStatus(error.message);
  }
}

async function submitUpload(event) {
  event.preventDefault();
  const files = Array.from(elements.fileInput.files || []);

  if (files.length === 0) {
    return;
  }

  setFileDrawerStatus("Uploading");

  try {
    await uploadFiles({
      userId: getUserId(),
      sessionUuid: getSessionUuid(),
      files,
    });
    elements.fileInput.value = "";
    await refreshFiles();
  } catch (error) {
    setFileDrawerStatus(error.message);
  }
}

elements.newSessionButton.addEventListener("click", () => {
  const userId = getUserId();
  const session = createSession(userId, randomUuid());
  closeCurrentSource();
  resetChatHistory();
  elements.sessionUuidInput.value = session.uuid;
  setActiveSessionLabel(session.uuid);
  renderSessionList(loadSessions(userId), session.uuid);
  renderStoredMessages(state.chatHistory);
  setStatus("idle", "Idle");
});

elements.userIdInput.addEventListener("change", hydrateSessionUi);

elements.sessionList.addEventListener("click", (event) => {
  const deleteButton = event.target.closest(".session-delete");
  if (deleteButton) {
    deleteSessionAndSelectNext(deleteButton.dataset.uuid);
    return;
  }

  const item = event.target.closest(".session-select");
  if (item) {
    switchSession(item.dataset.uuid);
  }
});

elements.fileDrawerToggle.addEventListener("click", () => {
  const nextOpen = !elements.fileDrawer.classList.contains("open");
  setFileDrawerOpen(nextOpen);
  if (nextOpen) {
    refreshFiles();
  }
});

elements.fileDrawerClose.addEventListener("click", () => {
  setFileDrawerOpen(false);
});

elements.fileRefreshButton.addEventListener("click", refreshFiles);
elements.fileUploadForm.addEventListener("submit", submitUpload);
elements.form.addEventListener("submit", submitMessage);
hydrateSessionUi();
renderEmptyState();

import { create } from "zustand";

import type { ChatMessage } from "@/lib/api";

export type SessionSummary = {
  uuid: string;
  title: string;
  updatedAt: number;
};

type SessionState = {
  userId: string;
  sessionUuid: string;
  sessions: SessionSummary[];
  fileDrawerOpen: boolean;
  fileDrawerWidth: number;
  setUserId(userId: string): void;
  setSessionUuid(sessionUuid: string): void;
  createSession(): SessionSummary;
  removeSession(uuid: string): string;
  renameSession(uuid: string, title: string): void;
  touchSession(uuid: string): void;
  setFileDrawerOpen(open: boolean): void;
  setFileDrawerWidth(width: number): void;
};

const DEFAULT_USER_ID = "local-user";
export const DEFAULT_SESSION_TITLE = "New session";
const MAX_SESSION_TITLE_LENGTH = 48;
const DEFAULT_FILE_DRAWER_WIDTH = 760;
const MIN_FILE_DRAWER_WIDTH = 320;
const MAX_FILE_DRAWER_WIDTH = 950;

export const useSessionStore = create<SessionState>((set) => {
  const userId = localStorage.getItem("minial:user-id") || DEFAULT_USER_ID;
  const initial = ensureSessionState(userId);

  return {
    userId,
    sessionUuid: initial.sessionUuid,
    sessions: initial.sessions,
    fileDrawerOpen: false,
    fileDrawerWidth: getFileDrawerWidth(),
    setUserId(nextUserId) {
      const cleanUserId = nextUserId.trim() || DEFAULT_USER_ID;
      localStorage.setItem("minial:user-id", cleanUserId);
      const next = ensureSessionState(cleanUserId);
      set({
        userId: cleanUserId,
        sessionUuid: next.sessionUuid,
        sessions: next.sessions,
      });
    },
    setSessionUuid(sessionUuid) {
      set((current) => {
        setActiveSessionUuid(current.userId, sessionUuid);
        return { sessionUuid };
      });
    },
    createSession() {
      const session = createSessionSummary();
      set((current) => {
        const sessions = [session, ...current.sessions];
        saveSessions(current.userId, sessions);
        setActiveSessionUuid(current.userId, session.uuid);
        return {
          sessionUuid: session.uuid,
          sessions,
        };
      });
      return session;
    },
    removeSession(uuid) {
      let nextSessionUuid = "";
      set((current) => {
        localStorage.removeItem(historyKey(current.userId, uuid));
        const remaining = current.sessions.filter((session) => session.uuid !== uuid);
        const sessions = remaining.length ? remaining : [createSessionSummary()];
        nextSessionUuid =
          uuid === current.sessionUuid
            ? sessions[0].uuid
            : current.sessionUuid;
        saveSessions(current.userId, sessions);
        setActiveSessionUuid(current.userId, nextSessionUuid);
        return {
          sessionUuid: nextSessionUuid,
          sessions,
        };
      });
      return nextSessionUuid;
    },
    renameSession(uuid, title) {
      const cleanTitle = cleanSessionTitle(title);
      if (!cleanTitle) {
        return;
      }

      set((current) => {
        const sessions = current.sessions.map((session) =>
          session.uuid === uuid ? { ...session, title: cleanTitle } : session,
        );
        saveSessions(current.userId, sessions);
        return { sessions };
      });
    },
    touchSession(uuid) {
      set((current) => {
        const sessions = current.sessions
          .map((session) =>
            session.uuid === uuid
              ? {
                  ...session,
                  updatedAt: Date.now(),
                }
              : session,
          )
          .sort((a, b) => b.updatedAt - a.updatedAt);
        saveSessions(current.userId, sessions);
        return { sessions };
      });
    },
    setFileDrawerOpen(open) {
      set({ fileDrawerOpen: open });
    },
    setFileDrawerWidth(width) {
      const cleanWidth = clampFileDrawerWidth(width);
      localStorage.setItem("minial:file-drawer-width", String(cleanWidth));
      set({ fileDrawerWidth: cleanWidth });
    },
  };
});

export function getSessions(userId: string): SessionSummary[] {
  return readJson<SessionSummary[]>(sessionsKey(userId), []);
}

export function getSessionHistory(userId: string, uuid: string): ChatMessage[] {
  return readJson<ChatMessage[]>(historyKey(userId, uuid), []);
}

export function saveSessionHistory(
  userId: string,
  uuid: string,
  messages: ChatMessage[],
) {
  localStorage.setItem(historyKey(userId, uuid), JSON.stringify(messages));
}

function saveSessions(userId: string, sessions: SessionSummary[]) {
  localStorage.setItem(sessionsKey(userId), JSON.stringify(sessions));
}

function ensureSessionState(userId: string): {
  sessionUuid: string;
  sessions: SessionSummary[];
} {
  const storedSessions = getSessions(userId);
  const sessions = storedSessions.length ? storedSessions : [createSessionSummary()];
  const activeSessionUuid = getActiveSessionUuid(userId);
  const sessionUuid = sessions.some((session) => session.uuid === activeSessionUuid)
    ? activeSessionUuid!
    : sessions[0].uuid;

  saveSessions(userId, sessions);
  setActiveSessionUuid(userId, sessionUuid);
  return { sessionUuid, sessions };
}

function createSessionSummary(): SessionSummary {
  return {
    uuid: crypto.randomUUID(),
    title: DEFAULT_SESSION_TITLE,
    updatedAt: Date.now(),
  };
}

function cleanSessionTitle(title: string): string {
  return title.trim().slice(0, MAX_SESSION_TITLE_LENGTH);
}

function getActiveSessionUuid(userId: string) {
  return localStorage.getItem(activeKey(userId));
}

function setActiveSessionUuid(userId: string, uuid: string) {
  localStorage.setItem(activeKey(userId), uuid);
}

function sessionsKey(userId: string) {
  return `minial:sessions:${userId}`;
}

function historyKey(userId: string, uuid: string) {
  return `minial:history:${userId}:${uuid}`;
}

function activeKey(userId: string) {
  return `minial:active-session:${userId}`;
}

function getFileDrawerWidth() {
  const value = Number(localStorage.getItem("minial:file-drawer-width"));
  if (!value || value === 420) {
    return DEFAULT_FILE_DRAWER_WIDTH;
  }
  return clampFileDrawerWidth(value);
}

function clampFileDrawerWidth(width: number) {
  return Math.min(
    MAX_FILE_DRAWER_WIDTH,
    Math.max(MIN_FILE_DRAWER_WIDTH, Math.round(width)),
  );
}

function readJson<T>(key: string, fallback: T): T {
  const value = localStorage.getItem(key);

  if (!value) {
    return fallback;
  }

  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}

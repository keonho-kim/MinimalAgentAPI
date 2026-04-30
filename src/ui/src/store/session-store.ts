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
  fileDrawerOpen: boolean;
  setUserId(userId: string): void;
  setSessionUuid(sessionUuid: string): void;
  setFileDrawerOpen(open: boolean): void;
};

const DEFAULT_USER_ID = "local-user";

export const useSessionStore = create<SessionState>((set) => {
  const userId = localStorage.getItem("minial:user-id") || DEFAULT_USER_ID;
  const activeSession = getActiveSessionUuid(userId) || createSession(userId).uuid;

  return {
    userId,
    sessionUuid: activeSession,
    fileDrawerOpen: false,
    setUserId(nextUserId) {
      const cleanUserId = nextUserId.trim() || DEFAULT_USER_ID;
      localStorage.setItem("minial:user-id", cleanUserId);
      const sessionUuid =
        getActiveSessionUuid(cleanUserId) || createSession(cleanUserId).uuid;
      set({ userId: cleanUserId, sessionUuid });
    },
    setSessionUuid(sessionUuid) {
      set((current) => {
        setActiveSessionUuid(current.userId, sessionUuid);
        return { sessionUuid };
      });
    },
    setFileDrawerOpen(open) {
      set({ fileDrawerOpen: open });
    },
  };
});

export function createSession(userId: string): SessionSummary {
  const session: SessionSummary = {
    uuid: crypto.randomUUID(),
    title: "New session",
    updatedAt: Date.now(),
  };
  const sessions = [session, ...getSessions(userId)];
  saveSessions(userId, sessions);
  setActiveSessionUuid(userId, session.uuid);
  return session;
}

export function getSessions(userId: string): SessionSummary[] {
  return readJson<SessionSummary[]>(sessionsKey(userId), []);
}

export function deleteSession(userId: string, uuid: string): SessionSummary[] {
  const sessions = getSessions(userId).filter((session) => session.uuid !== uuid);
  localStorage.removeItem(historyKey(userId, uuid));
  saveSessions(userId, sessions);
  return sessions;
}

export function touchSession(userId: string, uuid: string, title: string) {
  const sessions = getSessions(userId);
  const next = sessions
    .map((session) =>
      session.uuid === uuid
        ? { ...session, title: title.slice(0, 48) || "New session", updatedAt: Date.now() }
        : session,
    )
    .sort((a, b) => b.updatedAt - a.updatedAt);
  saveSessions(userId, next);
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

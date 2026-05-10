import type { DragEvent } from "react";

export const MIN_DRAWER_WIDTH = 320;
export const DEFAULT_DRAWER_WIDTH = 760;
export const MAX_DRAWER_WIDTH = 950;
export const VIEWPORT_PADDING = 64;
export const DRAWER_KEYBOARD_STEP = 24;
export const SEARCH_LIMIT = 50;

export function clampDrawerWidth(width: number) {
  return Math.min(maxViewportWidth(), Math.max(MIN_DRAWER_WIDTH, Math.round(width)));
}

export function maxViewportWidth() {
  if (typeof window === "undefined") {
    return DEFAULT_DRAWER_WIDTH;
  }
  return Math.max(
    MIN_DRAWER_WIDTH,
    Math.min(MAX_DRAWER_WIDTH, window.innerWidth - VIEWPORT_PADDING),
  );
}

export function hasDraggedFiles(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.types).includes("Files");
}

export function drawerStatus(
  status: string,
  searchQuery: string,
  searchQueryResult: {
    error: unknown;
    isFetching: boolean;
  },
) {
  if (searchQuery && searchQueryResult.isFetching) {
    return "검색 중";
  }
  if (searchQuery && searchQueryResult.error) {
    return "파일 시스템에 연결할 수 없습니다. 백엔드를 확인한 뒤 새로고침해 주세요.";
  }
  if (isFailureStatus(status)) {
    return "파일 시스템에 연결할 수 없습니다. 백엔드를 확인한 뒤 새로고침해 주세요.";
  }
  if (status === "Ready") {
    return "";
  }
  if (status === "Loading") {
    return "불러오는 중";
  }
  if (status === "Uploading") {
    return "업로드 중";
  }
  if (status === "Deleting") {
    return "삭제 중";
  }
  if (status === "Moving") {
    return "이동 중";
  }
  if (status === "Renaming") {
    return "이름 변경 중";
  }
  return status;
}

function isFailureStatus(status: string) {
  return /failed|error|cannot|unable/i.test(status);
}

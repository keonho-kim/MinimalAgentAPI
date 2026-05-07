import { lazy, Suspense, useCallback, useMemo, useRef, useState } from "react";
import type { DragEvent, FormEvent, ReactNode } from "react";

import { ChatComposer } from "@/components/chat/chat-composer";
import type {
  ComposerEditorHandle,
  ComposerSubmitPayload,
} from "@/lib/composer-editor";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { ChatHeader } from "@/components/layout/chat-header";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useChatStream } from "@/hooks/use-chat-stream";
import { useFilePreview } from "@/hooks/use-file-preview";
import { useHitlApproval } from "@/hooks/use-hitl-approval";
import { useWorkspaceFiles } from "@/hooks/use-workspace-files";
import type { FsListItem } from "@/lib/api";
import {
  fileMentionAttachmentFromDragPayload,
  readFileMentionDragPayload,
  toAgentFileHref,
} from "@/lib/file-mentions";
import { createId } from "@/lib/id";
import { isPreviewSupported } from "@/lib/preview-support";
import { useSessionStore } from "@/store/session-store";

const FilePreviewSheet = lazy(loadFilePreviewSheet);
const FileDrawer = lazy(() =>
  import("@/components/workspace/file-drawer").then((module) => ({
    default: module.FileDrawer,
  })),
);
const HitlApprovalDialog = lazy(() =>
  import("@/components/hitl/approval-dialog").then((module) => ({
    default: module.HitlApprovalDialog,
  })),
);

function loadFilePreviewSheet() {
  return import("@/components/preview/file-preview-sheet")
    .then((module) => ({
      default: module.FilePreviewSheet,
    }))
    .catch((error) => {
      recoverFromStaleUiChunk();
      throw error;
    });
}

function recoverFromStaleUiChunk() {
  const key = "minial:preview-chunk-reload";
  if (sessionStorage.getItem(key) === "1") {
    return;
  }
  sessionStorage.setItem(key, "1");
  window.location.reload();
}

export function App() {
  return (
    <TooltipProvider>
      <MinimalAgentShell />
    </TooltipProvider>
  );
}

function MinimalAgentShell() {
  const {
    userId,
    sessionUuid,
    sessions,
    fileDrawerOpen,
    fileDrawerWidth,
    setUserId,
    setSessionUuid,
    createSession,
    removeSession: removeStoredSession,
    renameSession,
    touchSession,
    setFileDrawerOpen,
    setFileDrawerWidth,
  } = useSessionStore();
  const markChatResumingRef = useRef<(() => void) | null>(null);
  const composerRef = useRef<ComposerEditorHandle | null>(null);
  const [composerUploadError, setComposerUploadError] = useState<string | null>(
    null,
  );
  const [globalDropActive, setGlobalDropActive] = useState(false);
  const currentSession = useMemo(
    () => sessions.find((session) => session.uuid === sessionUuid) ?? sessions[0],
    [sessionUuid, sessions],
  );
  const hitl = useHitlApproval({
    onResuming() {
      markChatResumingRef.current?.();
    },
  });
  const chat = useChatStream({
    userId,
    sessionUuid,
    currentSessionTitle: currentSession?.title,
    renameSession,
    touchSession,
    onBeforeSubmit() {
      hitl.clearState();
    },
    onHitlRequest: hitl.openRequest,
    onHitlResumed: hitl.clearDialogState,
    onStreamCreated: hitl.beginStream,
    onStreamCleared: hitl.clearState,
  });
  const workspaceFiles = useWorkspaceFiles({ userId, sessionUuid });
  const filePreview = useFilePreview({ userId, sessionUuid });
  markChatResumingRef.current = chat.markResuming;

  const switchSession = useCallback((nextUuid: string) => {
    chat.closeStream();
    hitl.clearState();
    setComposerUploadError(null);
    composerRef.current?.clear();
    setSessionUuid(nextUuid);
    chat.loadSession(nextUuid);
  }, [
    chat.closeStream,
    chat.loadSession,
    hitl.clearState,
    setSessionUuid,
  ]);

  const startSession = useCallback(() => {
    chat.generateTitleForSession({
      targetSessionUuid: sessionUuid,
      targetSessionTitle: currentSession?.title,
    });
    const session = createSession();
    switchSession(session.uuid);
  }, [
    chat.generateTitleForSession,
    createSession,
    currentSession?.title,
    sessionUuid,
    switchSession,
  ]);

  const removeSession = useCallback((uuid: string) => {
    const nextSessionUuid = removeStoredSession(uuid);
    if (uuid !== sessionUuid) {
      return;
    }
    switchSession(nextSessionUuid);
  }, [removeStoredSession, sessionUuid, switchSession]);

  const openFiles = useCallback(() => {
    setFileDrawerOpen(true);
    void workspaceFiles.refresh();
  }, [setFileDrawerOpen, workspaceFiles.refresh]);

  const openPreview = useCallback(
    (file: FsListItem) => {
      filePreview.openPreview(file);
    },
    [filePreview.openPreview],
  );

  const deleteFile = useCallback(
    async (file: FsListItem) => {
      await workspaceFiles.deleteFile(file);
      if (previewIsAffected(file, filePreview.activePath)) {
        filePreview.closePreview();
      }
    },
    [filePreview.activePath, filePreview.closePreview, workspaceFiles.deleteFile],
  );

  const movePath = useCallback(
    async (file: FsListItem, destinationPath: string) => {
      await workspaceFiles.movePath({ file, destinationPath });
      if (previewIsAffected(file, filePreview.activePath)) {
        filePreview.closePreview();
      }
    },
    [filePreview.activePath, filePreview.closePreview, workspaceFiles.movePath],
  );

  const renamePath = useCallback(
    async (file: FsListItem, name: string) => {
      await workspaceFiles.renamePath({ file, name });
      if (previewIsAffected(file, filePreview.activePath)) {
        filePreview.closePreview();
      }
    },
    [filePreview.activePath, filePreview.closePreview, workspaceFiles.renamePath],
  );

  const refreshFiles = useCallback(() => {
    void workspaceFiles.refresh();
  }, [workspaceFiles.refresh]);

  const refreshPreview = useCallback(() => {
    void filePreview.refresh();
  }, [filePreview.refresh]);

  const approveHitl = useCallback(() => {
    void hitl.submit("approve");
  }, [hitl.submit]);

  const rejectHitl = useCallback(() => {
    void hitl.submit("reject");
  }, [hitl.submit]);

  const submitHitlEdit = useCallback(() => {
    void hitl.submit("edit");
  }, [hitl.submit]);

  const uploadFiles = useCallback(
    async (
      files: File[],
      { insertIntoComposer }: { insertIntoComposer: boolean },
    ) => {
      setComposerUploadError(null);
      try {
        const response = await workspaceFiles.uploadSelectedFiles(files);
        const results = response.uploaded_files.map((file, index) => ({
          ...file,
          originalName: files[index]?.name ?? file.filename,
        }));
        const uploaded = results.filter(
          (file): file is typeof file & { path: string } =>
            file.status === "converted" && Boolean(file.path),
        );
        const failed = results.filter(
          (file) => file.status !== "converted" || !file.path,
        );

        if (insertIntoComposer && uploaded.length) {
          composerRef.current?.insertFileMentions(
            uploaded.map((file) => ({
              id: createId(),
              label: file.originalName,
              href: toAgentFileHref(file.path),
            })),
          );
        }

        if (failed.length) {
          setComposerUploadError(
            "하나 이상의 파일 업로드에 실패했습니다.",
          );
        }
      } catch {
        setComposerUploadError("업로드에 실패했습니다.");
      }
    },
    [
      workspaceFiles.uploadSelectedFiles,
    ],
  );

  const uploadComposerFiles = useCallback(
    (files: File[]) => uploadFiles(files, { insertIntoComposer: true }),
    [uploadFiles],
  );

  const uploadDrawerFiles = useCallback(
    (files: File[]) => uploadFiles(files, { insertIntoComposer: false }),
    [uploadFiles],
  );

  const globalDropDisabled = chat.chatBlocked || workspaceFiles.uploadPending;

  const handleGlobalDragOver = useCallback(
    (event: DragEvent<HTMLElement>) => {
      if (
        (!hasDraggedFiles(event) && !hasDraggedFileMention(event)) ||
        globalDropDisabled
      ) {
        return;
      }
      event.preventDefault();
      if (hasDraggedFiles(event)) {
        setGlobalDropActive(true);
      }
    },
    [globalDropDisabled],
  );

  const handleGlobalDragLeave = useCallback((event: DragEvent<HTMLElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      setGlobalDropActive(false);
    }
  }, []);

  const handleGlobalDrop = useCallback(
    (event: DragEvent<HTMLElement>) => {
      const fileMentionPayload = readFileMentionDragPayload(event.dataTransfer);
      if (fileMentionPayload) {
        event.preventDefault();
        setGlobalDropActive(false);
        if (!globalDropDisabled) {
          composerRef.current?.insertFileMentions([
            fileMentionAttachmentFromDragPayload(fileMentionPayload),
          ]);
        }
        return;
      }

      if (!hasDraggedFiles(event)) {
        return;
      }
      event.preventDefault();
      setGlobalDropActive(false);
      if (globalDropDisabled) {
        return;
      }
      void uploadComposerFiles(Array.from(event.dataTransfer.files));
    },
    [globalDropDisabled, uploadComposerFiles],
  );

  const submitComposerMessage = useCallback(
    async (
      event: FormEvent<HTMLFormElement>,
      payload: ComposerSubmitPayload,
    ) => {
      const submitted = await chat.submitMessage(event, payload);
      if (submitted) {
        setComposerUploadError(null);
      }
      return submitted;
    },
    [chat.submitMessage],
  );

  return (
    <AppShell
      dropActive={globalDropActive}
      onDragLeave={handleGlobalDragLeave}
      onDragOver={handleGlobalDragOver}
      onDrop={handleGlobalDrop}
      sidebar={
        <AppSidebar
          sessionUuid={sessionUuid}
          sessions={sessions}
          userId={userId}
          onNewSession={startSession}
          onRemoveSession={removeSession}
          onSwitchSession={switchSession}
          onUserIdChange={setUserId}
        />
      }
    >
      <ChatPane
        composer={
          <ChatComposer
            disabled={chat.chatBlocked || workspaceFiles.uploadPending}
            ref={composerRef}
            sessionUuid={sessionUuid}
            uploadError={composerUploadError}
            uploadPending={workspaceFiles.uploadPending}
            userId={userId}
            onSubmit={submitComposerMessage}
            onUploadFiles={uploadComposerFiles}
          />
        }
        header={
          <ChatHeader
            currentTitle={currentSession?.title}
            sessionUuid={sessionUuid}
            sessions={sessions}
            userId={userId}
            onNewSession={startSession}
            onOpenFiles={openFiles}
            onSwitchSession={switchSession}
            onUserIdChange={setUserId}
          />
        }
        messages={<ChatMessageList messages={chat.uiMessages} />}
      />
      {fileDrawerOpen ? (
        <Suspense fallback={null}>
          <FileDrawer
            drawerWidth={fileDrawerWidth}
            files={workspaceFiles.files}
            isPreviewSupported={isPreviewSupported}
            operationPendingPath={workspaceFiles.operationPendingPath}
            open={fileDrawerOpen}
            status={workspaceFiles.status}
            onDelete={deleteFile}
            onDrawerWidthChange={setFileDrawerWidth}
            onMove={movePath}
            onOpenChange={setFileDrawerOpen}
            onPreview={openPreview}
            onRefresh={refreshFiles}
            onRename={renamePath}
            onUploadFiles={uploadDrawerFiles}
            sessionUuid={sessionUuid}
            userId={userId}
          />
        </Suspense>
      ) : null}
      {filePreview.open ? (
        <Suspense fallback={null}>
          <FilePreviewSheet
            open={filePreview.open}
            preview={filePreview.preview}
            status={filePreview.status}
            onOpenChange={filePreview.setOpen}
            onRefresh={refreshPreview}
          />
        </Suspense>
      ) : null}
      {hitl.request ? (
        <Suspense fallback={null}>
          <HitlApprovalDialog
            drafts={hitl.drafts}
            mode={hitl.mode}
            request={hitl.request}
            rejectMessage={hitl.rejectMessage}
            status={hitl.status}
            submitting={hitl.submitting}
            onApprove={approveHitl}
            onDraftChange={hitl.updateDraft}
            onModeChange={hitl.setMode}
            onReject={rejectHitl}
            onRejectMessageChange={hitl.setRejectMessage}
            onSubmitEdit={submitHitlEdit}
          />
        </Suspense>
      ) : null}
    </AppShell>
  );
}

function AppShell({
  children,
  dropActive,
  onDragLeave,
  onDragOver,
  onDrop,
  sidebar,
}: {
  children: ReactNode;
  dropActive: boolean;
  onDragLeave(event: DragEvent<HTMLElement>): void;
  onDragOver(event: DragEvent<HTMLElement>): void;
  onDrop(event: DragEvent<HTMLElement>): void;
  sidebar: ReactNode;
}) {
  return (
    <main
      className="relative flex h-dvh min-h-0 overflow-hidden bg-background text-foreground"
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {sidebar}
      {children}
      {dropActive ? (
        <div className="pointer-events-none absolute inset-0 z-20 grid place-items-center border-2 border-dashed border-ring bg-background/70 text-sm font-medium text-foreground">
          파일을 놓으면 업로드 후 첨부됩니다.
        </div>
      ) : null}
    </main>
  );
}

function ChatPane({
  composer,
  header,
  messages,
}: {
  composer: ReactNode;
  header: ReactNode;
  messages: ReactNode;
}) {
  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      {header}
      {messages}
      {composer}
    </section>
  );
}

function hasDraggedFiles(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.types).includes("Files");
}

function hasDraggedFileMention(event: DragEvent<HTMLElement>) {
  return Array.from(event.dataTransfer.types).includes(
    "application/x-minimal-agent-file",
  );
}

function previewIsAffected(file: FsListItem, activePath: string | null) {
  if (!activePath) {
    return false;
  }
  if (file.type === "file") {
    return normalizeWorkspacePath(activePath) === normalizeWorkspacePath(file.path);
  }
  const parent = normalizeWorkspacePath(file.path);
  const child = normalizeWorkspacePath(activePath);
  return child === parent || child.startsWith(`${parent}/`);
}

function normalizeWorkspacePath(path: string) {
  const trimmed = path.trim();
  if (!trimmed || trimmed === "/") {
    return "/";
  }
  return `/${trimmed.replace(/^\/+/, "").replace(/\/+$/, "")}`;
}

import { lazy, Suspense, useCallback, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ChatComposer } from "@/components/chat/chat-composer";
import type {
  ComposerEditorHandle,
  ComposerSubmitPayload,
} from "@/lib/composer-editor";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { ChatHeader } from "@/components/layout/chat-header";
import { previewIsAffected } from "@/components/layout/shell-file-actions";
import { AppShell, ChatPane } from "@/components/layout/shell-layout";
import { useChatStream } from "@/hooks/use-chat-stream";
import { useFilePreview } from "@/hooks/use-file-preview";
import { useGlobalFileDrop } from "@/hooks/use-global-file-drop";
import { useHitlApproval } from "@/hooks/use-hitl-approval";
import { useShellUploads } from "@/hooks/use-shell-uploads";
import { useWorkspaceFiles } from "@/hooks/use-workspace-files";
import type { FsListItem } from "@/lib/api";
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

export function MinimalAgentShell() {
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
  const [fileDrawerFocusPath, setFileDrawerFocusPath] = useState<string | null>(
    null,
  );
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
  const uploads = useShellUploads({
    composerRef,
    uploadSelectedFiles: workspaceFiles.uploadSelectedFiles,
  });
  const globalDrop = useGlobalFileDrop({
    composerRef,
    disabled: chat.chatBlocked || workspaceFiles.uploadPending,
    uploadFiles: uploads.uploadComposerFiles,
  });
  markChatResumingRef.current = chat.markResuming;

  const switchSession = useCallback((nextUuid: string) => {
    chat.closeStream();
    hitl.clearState();
    uploads.clearUploadError();
    composerRef.current?.clear();
    setSessionUuid(nextUuid);
    chat.loadSession(nextUuid);
  }, [
    chat.closeStream,
    chat.loadSession,
    hitl.clearState,
    setSessionUuid,
    uploads.clearUploadError,
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
    setFileDrawerFocusPath(null);
    setFileDrawerOpen(true);
    void workspaceFiles.refresh();
  }, [setFileDrawerOpen, workspaceFiles.refresh]);

  const openActivityFile = useCallback(
    (path: string) => {
      setFileDrawerFocusPath(path);
      setFileDrawerOpen(true);
      void workspaceFiles.refresh();
    },
    [setFileDrawerOpen, workspaceFiles.refresh],
  );

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

  const submitComposerMessage = useCallback(
    async (
      event: FormEvent<HTMLFormElement>,
      payload: ComposerSubmitPayload,
    ) => {
      const submitted = await chat.submitMessage(event, payload);
      if (submitted) {
        uploads.clearUploadError();
      }
      return submitted;
    },
    [chat.submitMessage, uploads.clearUploadError],
  );

  return (
    <AppShell
      dropActive={globalDrop.dropActive}
      onDragLeave={globalDrop.handleDragLeave}
      onDragOver={globalDrop.handleDragOver}
      onDrop={globalDrop.handleDrop}
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
            uploadError={uploads.uploadError}
            uploadPending={workspaceFiles.uploadPending}
            userId={userId}
            onSubmit={submitComposerMessage}
            onUploadFiles={uploads.uploadComposerFiles}
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
        messages={
          <ChatMessageList
            messages={chat.uiMessages}
            onOpenActivityFile={openActivityFile}
          />
        }
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
            onUploadFiles={uploads.uploadDrawerFiles}
            focusPath={fileDrawerFocusPath}
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
            sessionUuid={sessionUuid}
            status={filePreview.status}
            userId={userId}
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

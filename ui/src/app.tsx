import { lazy, Suspense, useCallback, useMemo, useRef } from "react";

import { ChatComposer } from "@/components/chat/chat-composer";
import { ChatMessageList } from "@/components/chat/chat-message-list";
import { FileDrawer } from "@/components/workspace/file-drawer";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { ChatHeader } from "@/components/layout/chat-header";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useChatStream } from "@/hooks/use-chat-stream";
import { useFileMentions } from "@/hooks/use-file-mentions";
import { useFilePreview } from "@/hooks/use-file-preview";
import { useHitlApproval } from "@/hooks/use-hitl-approval";
import { useSkillMentions } from "@/hooks/use-skill-mentions";
import { useWorkspaceFiles } from "@/hooks/use-workspace-files";
import type { FsListItem } from "@/lib/api";
import { isPreviewSupported } from "@/lib/preview-support";
import { useSessionStore } from "@/store/session-store";

const FilePreviewSheet = lazy(() =>
  import("@/components/preview/file-preview-sheet").then((module) => ({
    default: module.FilePreviewSheet,
  })),
);
const HitlApprovalDialog = lazy(() =>
  import("@/components/hitl/approval-dialog").then((module) => ({
    default: module.HitlApprovalDialog,
  })),
);

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
    setUserId,
    setSessionUuid,
    createSession,
    removeSession: removeStoredSession,
    renameSession,
    touchSession,
    setFileDrawerOpen,
  } = useSessionStore();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const markChatResumingRef = useRef<(() => void) | null>(null);
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
      mentions.close();
      skillMentions.close();
      hitl.clearState();
    },
    onHitlRequest: hitl.openRequest,
    onHitlResumed: hitl.clearDialogState,
    onStreamCreated: hitl.beginStream,
    onStreamCleared: hitl.clearState,
  });
  const mentions = useFileMentions({
    userId,
    sessionUuid,
    message: chat.message,
    insertFileMention: chat.insertMentionRange,
    textareaRef,
  });
  const skillMentions = useSkillMentions({
    userId,
    sessionUuid,
    message: chat.message,
    insertMentionRange: chat.insertMentionRange,
    textareaRef,
  });
  const workspaceFiles = useWorkspaceFiles({ userId, sessionUuid });
  const filePreview = useFilePreview({ userId, sessionUuid });
  markChatResumingRef.current = chat.markResuming;

  const switchSession = useCallback((nextUuid: string) => {
    chat.closeStream();
    mentions.close();
    skillMentions.close();
    hitl.clearState();
    setSessionUuid(nextUuid);
    chat.loadSession(nextUuid);
  }, [
    chat.closeStream,
    chat.loadSession,
    hitl.clearState,
    mentions.close,
    skillMentions.close,
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

  return (
    <main className="flex min-h-svh overflow-hidden bg-background text-foreground">
      <AppSidebar
        sessionUuid={sessionUuid}
        sessions={sessions}
        status={chat.status}
        userId={userId}
        onNewSession={startSession}
        onRemoveSession={removeSession}
        onSwitchSession={switchSession}
        onUserIdChange={setUserId}
      />

      <section className="flex min-w-0 flex-1 flex-col">
        <ChatHeader
          currentTitle={currentSession?.title}
          sessionUuid={sessionUuid}
          sessions={sessions}
          status={chat.status}
          userId={userId}
          onNewSession={startSession}
          onOpenFiles={openFiles}
          onSwitchSession={switchSession}
          onUserIdChange={setUserId}
        />

        <ChatMessageList messages={chat.uiMessages} />

        <ChatComposer
          disabled={chat.chatBlocked}
          mentionActive={mentions.active}
          mentionIndex={mentions.activeIndex}
          mentionMatches={mentions.matches}
          mentionStatus={mentions.status}
          message={chat.message}
          mentionRanges={chat.mentionRanges}
          skillMentionActive={skillMentions.active}
          skillMentionIndex={skillMentions.activeIndex}
          skillMentionMatches={skillMentions.matches}
          skillMentionStatus={skillMentions.status}
          textareaRef={textareaRef}
          onCursorSync={(element) => {
            mentions.syncCursor(element);
            skillMentions.syncCursor(element);
          }}
          onMentionKeyDown={mentions.handleKeyDown}
          onMentionSelect={mentions.select}
          onSkillMentionKeyDown={skillMentions.handleKeyDown}
          onSkillMentionSelect={skillMentions.select}
          onMessageChange={chat.setMessage}
          onSubmit={chat.submitMessage}
        />
      </section>

      <FileDrawer
        files={workspaceFiles.files}
        isPreviewSupported={isPreviewSupported}
        open={fileDrawerOpen}
        status={workspaceFiles.status}
        onOpenChange={setFileDrawerOpen}
        onPreview={openPreview}
        onRefresh={refreshFiles}
        onUpload={workspaceFiles.upload}
      />
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
    </main>
  );
}

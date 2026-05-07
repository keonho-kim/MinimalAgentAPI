import { EditorContent, useEditor } from "@tiptap/react";
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  composerDocFromText,
  composerPayloadFromJson,
  type ComposerEditorRuntimeHandle,
} from "@/lib/composer-editor";
import { composerExtensions, insertFileMentions } from "@/lib/composer-tiptap";
import type { FileMentionAttachment } from "@/lib/file-mentions";

type ChatComposerEditorProps = {
  disabled: boolean;
  initialText: string;
  pendingAttachments: FileMentionAttachment[];
  sessionUuid: string;
  userId: string;
  onPendingAttachmentsFlushed(): void;
  onEmptyChange(empty: boolean): void;
  onSubmitRequest(): void;
};

export const ChatComposerEditor = forwardRef<
  ComposerEditorRuntimeHandle,
  ChatComposerEditorProps
>(function ChatComposerEditor(
  {
    disabled,
    initialText,
    pendingAttachments,
    sessionUuid,
    userId,
    onEmptyChange,
    onPendingAttachmentsFlushed,
    onSubmitRequest,
  },
  ref,
) {
  const [editorEmpty, setEditorEmpty] = useState(true);
  const suggestionActiveRef = useRef(false);
  const extensions = useMemo(
    () =>
      composerExtensions({
        sessionUuid,
        userId,
        onSuggestionActiveChange(active) {
          suggestionActiveRef.current = active;
        },
      }),
    [sessionUuid, userId],
  );
  const editor = useEditor(
    {
      content: composerDocFromText(initialText),
      editable: !disabled,
      onCreate({ editor }) {
        editor.commands.setTextSelection(editor.state.doc.content.size);
        setEditorEmpty(editor.isEmpty);
        onEmptyChange(editor.isEmpty);
      },
      onUpdate({ editor }) {
        setEditorEmpty(editor.isEmpty);
        onEmptyChange(editor.isEmpty);
      },
      editorProps: {
        attributes: {
          "aria-label": "Message",
          class:
            "min-h-24 max-h-40 overflow-y-auto px-7 pb-2 pt-7 text-sm outline-none whitespace-pre-wrap break-words",
        },
        handleKeyDown(_view, event) {
          if (suggestionActiveRef.current) {
            return false;
          }
          if (event.key !== "Enter" || disabled || isComposing(event)) {
            return false;
          }
          if (event.shiftKey) {
            return false;
          }
          event.preventDefault();
          onSubmitRequest();
          return true;
        },
      },
      extensions,
    },
    [extensions, onEmptyChange],
  );

  useImperativeHandle(
    ref,
    () => ({
      clear() {
        editor?.commands.clearContent();
        onEmptyChange(true);
      },
      focus() {
        editor?.commands.focus();
      },
      getPayload() {
        return composerPayloadFromJson(editor?.getJSON() ?? composerDocFromText(""));
      },
      insertFileMentions(attachments) {
        insertFileMentions(editor, attachments);
      },
      isEmpty() {
        return editor?.isEmpty ?? true;
      },
    }),
    [editor, onEmptyChange],
  );

  useEffect(() => {
    editor?.setEditable(!disabled);
  }, [disabled, editor]);

  useEffect(() => {
    if (!editor || !pendingAttachments.length) {
      return;
    }

    insertFileMentions(editor, pendingAttachments);
    onPendingAttachmentsFlushed();
  }, [editor, onPendingAttachmentsFlushed, pendingAttachments]);

  return (
    <>
      {editorEmpty ? (
        <span className="pointer-events-none absolute left-7 top-7 text-sm text-muted-foreground">
          무엇을 도와드릴까요?
        </span>
      ) : null}
      <EditorContent editor={editor} />
    </>
  );
});

function isComposing(event: KeyboardEvent) {
  return event.isComposing || event.keyCode === 229;
}

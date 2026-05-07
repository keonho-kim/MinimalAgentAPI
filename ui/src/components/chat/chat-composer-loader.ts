let composerEditorPromise:
  | Promise<typeof import("@/components/chat/chat-composer-editor")>
  | null = null;

export function loadChatComposerEditor() {
  composerEditorPromise ??= import("@/components/chat/chat-composer-editor");
  return composerEditorPromise;
}

export function loadChatComposerEditorComponent() {
  return loadChatComposerEditor().then((module) => ({
    default: module.ChatComposerEditor,
  }));
}

export function preloadChatComposerEditor() {
  void loadChatComposerEditor();
}

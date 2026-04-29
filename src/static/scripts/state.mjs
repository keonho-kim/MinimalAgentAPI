export const state = {
  chatHistory: [],
  currentSource: null,
};

export function resetChatHistory() {
  state.chatHistory = [];
}

export function setCurrentSource(source) {
  state.currentSource = source;
}

export function closeCurrentSource() {
  if (state.currentSource) {
    state.currentSource.close();
    state.currentSource = null;
  }
}

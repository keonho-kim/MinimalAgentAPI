import type { ChatMessage } from "@/lib/api";

export function buildSessionTitleContext({
  userMessage,
  assistantMessage,
}: {
  userMessage: string;
  assistantMessage?: string;
}) {
  const cleanUserMessage = userMessage.trim();
  const cleanAssistantMessage = assistantMessage?.trim() ?? "";

  if (!cleanUserMessage) {
    return "";
  }

  if (!cleanAssistantMessage) {
    return `User:\n${cleanUserMessage}`;
  }

  return `User:\n${cleanUserMessage}\n\nAssistant:\n${cleanAssistantMessage}`;
}

export function firstCompletedExchangeTitleContext(history: ChatMessage[]) {
  const firstUserIndex = history.findIndex((message) => message.role === "user");
  if (firstUserIndex === -1) {
    return "";
  }

  const firstAssistant = history
    .slice(firstUserIndex + 1)
    .find((message) => message.role === "assistant");

  return buildSessionTitleContext({
    userMessage: history[firstUserIndex].content,
    assistantMessage: firstAssistant?.content,
  });
}

export function userMessageCount(history: ChatMessage[]) {
  return history.filter((message) => message.role === "user").length;
}

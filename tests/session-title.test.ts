import { expect, test } from "bun:test";

import {
  buildSessionTitleContext,
  firstCompletedExchangeTitleContext,
  userMessageCount,
} from "../ui/src/lib/session-title";

test("builds title context from user and assistant messages", () => {
  expect(
    buildSessionTitleContext({
      userMessage: "현재 폴더 파일 확인",
      assistantMessage: "현재 폴더에는 README.md가 있습니다.",
    }),
  ).toBe(
    "User:\n현재 폴더 파일 확인\n\nAssistant:\n현재 폴더에는 README.md가 있습니다.",
  );
});

test("builds title context from user message when assistant is missing", () => {
  expect(
    buildSessionTitleContext({
      userMessage: "현재 폴더 파일 확인",
    }),
  ).toBe("User:\n현재 폴더 파일 확인");
});

test("uses the first completed exchange from session history", () => {
  expect(
    firstCompletedExchangeTitleContext([
      { role: "user", content: "첫 질문" },
      { role: "assistant", content: "첫 답변" },
      { role: "user", content: "두 번째 질문" },
      { role: "assistant", content: "두 번째 답변" },
    ]),
  ).toBe("User:\n첫 질문\n\nAssistant:\n첫 답변");
});

test("counts user messages only", () => {
  expect(
    userMessageCount([
      { role: "user", content: "첫 질문" },
      { role: "assistant", content: "첫 답변" },
      { role: "user", content: "두 번째 질문" },
    ]),
  ).toBe(2);
});

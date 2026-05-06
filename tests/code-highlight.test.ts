import { expect, test } from "bun:test";

import {
  highlightCode,
  highlightedCodeBlock,
  languageForFilename,
  normalizeCodeLanguage,
} from "../ui/src/lib/code-highlight";

test("maps supported code filenames to highlight languages", () => {
  expect(languageForFilename("script.py")).toBe("python");
  expect(languageForFilename("app.tsx")).toBe("typescript");
  expect(languageForFilename("query.sql")).toBe("sql");
  expect(languageForFilename("index.html")).toBe("html");
  expect(languageForFilename("run.sh")).toBe("bash");
});

test("normalizes markdown fence aliases", () => {
  expect(normalizeCodeLanguage("js")).toBe("javascript");
  expect(normalizeCodeLanguage("tsx")).toBe("typescript");
  expect(normalizeCodeLanguage("shell")).toBe("bash");
  expect(normalizeCodeLanguage("unknown")).toBeNull();
});

test("highlights known code and escapes unknown code", () => {
  expect(highlightCode("const ok = true", "javascript")).toContain("hljs-keyword");
  expect(highlightCode("<script>", "unknown")).toBe("&lt;script&gt;");
});

test("renders markdown code block html with highlight classes", () => {
  const html = highlightedCodeBlock("select * from users", "sql");

  expect(html).toContain("language-sql");
  expect(html).toContain("hljs-keyword");
});

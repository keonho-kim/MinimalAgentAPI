import hljs from "highlight.js/lib/core";
import bash from "highlight.js/lib/languages/bash";
import css from "highlight.js/lib/languages/css";
import go from "highlight.js/lib/languages/go";
import java from "highlight.js/lib/languages/java";
import javascript from "highlight.js/lib/languages/javascript";
import json from "highlight.js/lib/languages/json";
import python from "highlight.js/lib/languages/python";
import sql from "highlight.js/lib/languages/sql";
import typescript from "highlight.js/lib/languages/typescript";
import xml from "highlight.js/lib/languages/xml";

const LANGUAGE_BY_EXTENSION: Record<string, string> = {
  bash: "bash",
  cjs: "javascript",
  css: "css",
  go: "go",
  htm: "html",
  html: "html",
  java: "java",
  js: "javascript",
  json: "json",
  jsx: "javascript",
  mjs: "javascript",
  py: "python",
  sh: "bash",
  sql: "sql",
  ts: "typescript",
  tsx: "typescript",
  zsh: "bash",
};

const LANGUAGE_ALIASES: Record<string, string> = {
  bash: "bash",
  css: "css",
  go: "go",
  golang: "go",
  html: "html",
  java: "java",
  javascript: "javascript",
  js: "javascript",
  json: "json",
  jsx: "javascript",
  py: "python",
  python: "python",
  sh: "bash",
  shell: "bash",
  sql: "sql",
  ts: "typescript",
  tsx: "typescript",
  typescript: "typescript",
  xml: "html",
  zsh: "bash",
};

hljs.registerLanguage("bash", bash);
hljs.registerLanguage("css", css);
hljs.registerLanguage("go", go);
hljs.registerLanguage("html", xml);
hljs.registerLanguage("java", java);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("json", json);
hljs.registerLanguage("python", python);
hljs.registerLanguage("sql", sql);
hljs.registerLanguage("typescript", typescript);

export function languageForExtension(extension: string) {
  return LANGUAGE_BY_EXTENSION[extension.toLowerCase()] ?? null;
}

export function languageForFilename(filename: string) {
  const extension = filename.split(".").pop()?.toLowerCase() ?? "";
  return languageForExtension(extension);
}

export function normalizeCodeLanguage(language: string | null | undefined) {
  if (!language) {
    return null;
  }
  const normalized = language.trim().toLowerCase().split(/\s+/)[0];
  return LANGUAGE_ALIASES[normalized] ?? null;
}

export function highlightCode(code: string, language: string | null | undefined) {
  const normalized = normalizeCodeLanguage(language);
  if (!normalized || !hljs.getLanguage(normalized)) {
    return escapeHtml(code);
  }
  return hljs.highlight(code, {
    language: normalized,
    ignoreIllegals: true,
  }).value;
}

export function highlightedCodeBlock(code: string, language: string | null | undefined) {
  const normalized = normalizeCodeLanguage(language);
  const highlighted = highlightCode(code, normalized);
  const languageClass = normalized ? ` language-${normalized}` : "";
  return `<pre><code class="hljs${languageClass}">${highlighted}</code></pre>`;
}

export function codeLanguageLabel(language: string | null | undefined) {
  const normalized = normalizeCodeLanguage(language);
  if (!normalized) {
    return "Plain text";
  }
  if (normalized === "html") {
    return "HTML";
  }
  if (normalized === "sql") {
    return "SQL";
  }
  return normalized[0].toUpperCase() + normalized.slice(1);
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

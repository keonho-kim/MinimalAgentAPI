import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import markdownItKatex from "markdown-it-katex";
import type Token from "markdown-it/lib/token.mjs";
import type StateCore from "markdown-it/lib/rules_core/state_core.mjs";

import { highlightedCodeBlock } from "@/lib/code-highlight";
import {
  isFileMentionHref,
  isSkillMentionHref,
  normalizeMarkdownFileMentionHrefs,
} from "@/lib/file-mentions";

const markdown = new MarkdownIt({
  breaks: true,
  highlight(value, language) {
    return highlightedCodeBlock(value, language);
  },
  html: true,
  linkify: true,
  typographer: true,
}).use(markdownItKatex, {
  output: "html",
  throwOnError: false,
});

markdown.core.ruler.after("inline", "skill_mentions", (state) => {
  for (const token of state.tokens) {
    if (token.type !== "inline" || !token.children?.length) {
      continue;
    }

    token.children = renderPlainSkillMentionTokens(state, token.children);
  }
});

const defaultLinkOpen =
  markdown.renderer.rules.link_open ??
  ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options));
const defaultLinkClose =
  markdown.renderer.rules.link_close ??
  ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options));

markdown.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const token = tokens[idx];
  const href = token.attrGet("href");

  if (href && (isFileMentionHref(href) || isSkillMentionHref(href))) {
    const renderEnv = env as { fileMentionDepth?: number };
    renderEnv.fileMentionDepth = (renderEnv.fileMentionDepth ?? 0) + 1;
    token.attrSet(
      "class",
      isSkillMentionHref(href) ? "skill-mention-pill" : "file-mention-pill",
    );
    token.attrs = token.attrs?.filter(([name]) => name !== "href") ?? null;
    token.tag = "span";
    return self.renderToken(tokens, idx, options);
  }

  if (href && /^(https?:|mailto:)/i.test(href)) {
    token.attrSet("target", "_blank");
    token.attrSet("rel", "noreferrer noopener");
  }

  return defaultLinkOpen(tokens, idx, options, env, self);
};

markdown.renderer.rules.link_close = (tokens, idx, options, env, self) => {
  const renderEnv = env as { fileMentionDepth?: number };
  if (renderEnv.fileMentionDepth && renderEnv.fileMentionDepth > 0) {
    renderEnv.fileMentionDepth -= 1;
    tokens[idx].tag = "span";
    return self.renderToken(tokens, idx, options);
  }

  return defaultLinkClose(tokens, idx, options, env, self);
};

export function renderSafeMarkdown(source: string) {
  const rendered = markdown.render(normalizeMarkdownFileMentionHrefs(source));

  return DOMPurify.sanitize(rendered, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ["class", "target"],
  });
}

function renderPlainSkillMentionTokens(state: StateCore, tokens: Token[]) {
  const nextTokens: Token[] = [];
  let linkDepth = 0;

  for (const token of tokens) {
    if (token.type === "link_open") {
      linkDepth += 1;
      nextTokens.push(token);
      continue;
    }

    if (token.type === "link_close") {
      linkDepth = Math.max(0, linkDepth - 1);
      nextTokens.push(token);
      continue;
    }

    if (token.type !== "text" || linkDepth > 0) {
      nextTokens.push(token);
      continue;
    }

    nextTokens.push(...splitPlainSkillMentionText(state, token));
  }

  return nextTokens;
}

function splitPlainSkillMentionText(state: StateCore, sourceToken: Token) {
  const tokens: Token[] = [];
  const pattern = /(^|[\s([{])(\$[A-Za-z_][A-Za-z0-9_.-]*)/g;
  let cursor = 0;

  for (const match of sourceToken.content.matchAll(pattern)) {
    const prefix = match[1] ?? "";
    const mention = match[2] ?? "";
    const mentionStart = (match.index ?? 0) + prefix.length;

    appendTextToken(
      state,
      tokens,
      sourceToken,
      sourceToken.content.slice(cursor, mentionStart),
    );
    appendSkillMentionToken(state, tokens, sourceToken, mention);
    cursor = mentionStart + mention.length;
  }

  appendTextToken(state, tokens, sourceToken, sourceToken.content.slice(cursor));
  return tokens.length ? tokens : [sourceToken];
}

function appendTextToken(
  state: StateCore,
  tokens: Token[],
  sourceToken: Token,
  content: string,
) {
  if (!content) {
    return;
  }

  const token = new state.Token("text", "", 0);
  token.content = content;
  token.level = sourceToken.level;
  tokens.push(token);
}

function appendSkillMentionToken(
  state: StateCore,
  tokens: Token[],
  sourceToken: Token,
  content: string,
) {
  const openToken = new state.Token("span_open", "span", 1);
  openToken.attrSet("class", "skill-mention-pill");
  openToken.level = sourceToken.level;

  const textToken = new state.Token("text", "", 0);
  textToken.content = content;
  textToken.level = sourceToken.level + 1;

  const closeToken = new state.Token("span_close", "span", -1);
  closeToken.level = sourceToken.level;

  tokens.push(openToken, textToken, closeToken);
}

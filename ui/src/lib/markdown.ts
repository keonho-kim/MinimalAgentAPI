import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import markdownItKatex from "markdown-it-katex";

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

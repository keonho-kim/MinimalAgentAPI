import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";
import markdownItKatex from "markdown-it-katex";

const markdown = new MarkdownIt({
  breaks: true,
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

markdown.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  const token = tokens[idx];
  const href = token.attrGet("href");

  if (href && /^(https?:|mailto:)/i.test(href)) {
    token.attrSet("target", "_blank");
    token.attrSet("rel", "noreferrer noopener");
  }

  return defaultLinkOpen(tokens, idx, options, env, self);
};

export function renderSafeMarkdown(source: string) {
  const rendered = markdown.render(source);

  return DOMPurify.sanitize(rendered, {
    USE_PROFILES: { html: true },
    ADD_ATTR: ["target"],
  });
}

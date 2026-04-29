const MarkdownIt = window.markdownit;
const DOMPurify = window.DOMPurify;
const katex = window.katex;

const markdown = new MarkdownIt({
  html: true,
  linkify: true,
  breaks: true,
});

const mathPlaceholders = new Map();

export function renderAssistantContent(rawText) {
  mathPlaceholders.clear();

  const withMath = replaceMath(rawText);
  const html = markdown.render(withMath);
  return DOMPurify.sanitize(html, {
    ADD_ATTR: ["target", "rel"],
  });
}

export function renderInto(element, rawText) {
  element.innerHTML = renderAssistantContent(rawText);
}

export function createDebouncedRenderer(element, delayMs = 60) {
  let timer = null;
  let latestText = "";

  return {
    schedule(rawText) {
      latestText = rawText;
      if (timer) {
        return;
      }

      timer = window.setTimeout(() => {
        timer = null;
        renderInto(element, latestText);
      }, delayMs);
    },
    flush(rawText = latestText) {
      if (timer) {
        window.clearTimeout(timer);
        timer = null;
      }
      latestText = rawText;
      renderInto(element, latestText);
    },
  };
}

function replaceMath(text) {
  const withoutBlocks = text.replace(/\$\$([\s\S]+?)\$\$/g, (_match, expression) =>
    createMathPlaceholder(expression, true),
  );

  return withoutBlocks.replace(
    /(^|[^\\])\$([^\n$]+?)\$/g,
    (_match, prefix, expression) =>
      `${prefix}${createMathPlaceholder(expression, false)}`,
  );
}

function createMathPlaceholder(expression, displayMode) {
  const key = `@@MINIAL_MATH_${mathPlaceholders.size}@@`;
  const rendered = katex.renderToString(expression.trim(), {
    displayMode,
    throwOnError: false,
    strict: "ignore",
  });

  mathPlaceholders.set(key, rendered);
  return key;
}

markdown.renderer.rules.text = (tokens, idx) => {
  const content = markdown.utils.escapeHtml(tokens[idx].content);
  return restoreMathPlaceholders(content);
};

function restoreMathPlaceholders(content) {
  let restored = content;
  for (const [key, value] of mathPlaceholders.entries()) {
    restored = restored.split(key).join(value);
  }
  return restored;
}

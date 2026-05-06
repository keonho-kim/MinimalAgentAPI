const PREVIEW_EXTENSIONS = new Set([
  "pdf",
  "py",
  "js",
  "jsx",
  "mjs",
  "cjs",
  "ts",
  "tsx",
  "sql",
  "html",
  "htm",
  "css",
  "java",
  "go",
  "sh",
  "bash",
  "zsh",
  "json",
  "docx",
  "pptx",
  "xlsx",
  "hwpx",
  "md",
  "markdown",
  "txt",
]);

export function isPreviewSupported(filename: string) {
  const extension = filename.split(".").pop()?.toLowerCase() ?? "";
  return PREVIEW_EXTENSIONS.has(extension);
}

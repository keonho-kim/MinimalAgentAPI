declare module "markdown-it-katex" {
  import type MarkdownIt from "markdown-it";

  type KatexOptions = {
    errorColor?: string;
    output?: "html" | "mathml" | "htmlAndMathml";
    throwOnError?: boolean;
  };

  const markdownItKatex: MarkdownIt.PluginWithOptions<KatexOptions>;
  export default markdownItKatex;
}

import {
  IconFileCode,
  IconFileDescription,
  IconFileMusic,
  IconFileTypeCss,
  IconFileTypeCsv,
  IconFileTypeDoc,
  IconFileTypeDocx,
  IconFileTypeHtml,
  IconFileTypeJpg,
  IconFileTypeJs,
  IconFileTypeJsx,
  IconFileTypePdf,
  IconFileTypePng,
  IconFileTypePpt,
  IconFileTypeSql,
  IconFileTypeSvg,
  IconFileTypeTs,
  IconFileTypeTsx,
  IconFileTypeTxt,
  IconFileTypeXls,
  IconFileTypeXml,
  IconFileTypeZip,
  IconFileUnknown,
  IconFileVector,
  IconFolder,
  IconFolderOpen,
  IconJson,
  IconMarkdown,
  IconVideo,
} from "@tabler/icons-react";
import type { Icon } from "@tabler/icons-react";

type FileIconType = "file" | "directory";

export type FileTreeIconInput = {
  name: string;
  type: FileIconType;
  isOpen?: boolean;
};

const EXTENSION_ICONS: Record<string, Icon> = {
  css: IconFileTypeCss,
  csv: IconFileTypeCsv,
  doc: IconFileTypeDoc,
  docx: IconFileTypeDocx,
  htm: IconFileTypeHtml,
  html: IconFileTypeHtml,
  jpeg: IconFileTypeJpg,
  jpg: IconFileTypeJpg,
  js: IconFileTypeJs,
  json: IconJson,
  jsx: IconFileTypeJsx,
  markdown: IconMarkdown,
  md: IconMarkdown,
  pdf: IconFileTypePdf,
  png: IconFileTypePng,
  ppt: IconFileTypePpt,
  pptx: IconFileTypePpt,
  sql: IconFileTypeSql,
  svg: IconFileTypeSvg,
  ts: IconFileTypeTs,
  tsx: IconFileTypeTsx,
  txt: IconFileTypeTxt,
  xls: IconFileTypeXls,
  xlsx: IconFileTypeXls,
  xml: IconFileTypeXml,
  zip: IconFileTypeZip,
};

const CODE_EXTENSIONS = new Set([
  "c",
  "cpp",
  "cs",
  "go",
  "java",
  "kt",
  "py",
  "rb",
  "rs",
  "sh",
  "swift",
]);

const AUDIO_EXTENSIONS = new Set(["aac", "flac", "m4a", "mp3", "ogg", "wav"]);
const VIDEO_EXTENSIONS = new Set(["avi", "m4v", "mov", "mp4", "mpeg", "webm"]);
const VECTOR_EXTENSIONS = new Set(["ai", "eps"]);

export function fileTreeIconFor({ name, type, isOpen = false }: FileTreeIconInput) {
  if (type === "directory") {
    return isOpen ? IconFolderOpen : IconFolder;
  }

  const extension = fileExtension(name);
  if (!extension) {
    return IconFileUnknown;
  }

  const exactIcon = EXTENSION_ICONS[extension];
  if (exactIcon) {
    return exactIcon;
  }
  if (CODE_EXTENSIONS.has(extension)) {
    return IconFileCode;
  }
  if (AUDIO_EXTENSIONS.has(extension)) {
    return IconFileMusic;
  }
  if (VIDEO_EXTENSIONS.has(extension)) {
    return IconVideo;
  }
  if (VECTOR_EXTENSIONS.has(extension)) {
    return IconFileVector;
  }
  if (extension === "hwpx" || extension === "hwp") {
    return IconFileDescription;
  }
  return IconFileUnknown;
}

export function FileTreeIcon({
  className,
  isOpen,
  name,
  type,
}: FileTreeIconInput & {
  className?: string;
}) {
  const Icon = fileTreeIconFor({ name, type, isOpen });

  return (
    <Icon
      aria-hidden
      className={className}
      focusable={false}
      stroke={1.8}
    />
  );
}

function fileExtension(name: string) {
  const cleanName = name.trim().toLowerCase();
  const lastDotIndex = cleanName.lastIndexOf(".");
  if (lastDotIndex <= 0 || lastDotIndex === cleanName.length - 1) {
    return "";
  }
  return cleanName.slice(lastDotIndex + 1);
}

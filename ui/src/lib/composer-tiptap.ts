import Document from "@tiptap/extension-document";
import HardBreak from "@tiptap/extension-hard-break";
import Mention from "@tiptap/extension-mention";
import Paragraph from "@tiptap/extension-paragraph";
import Text from "@tiptap/extension-text";
import type { Editor } from "@tiptap/react";
import type { SuggestionKeyDownProps, SuggestionProps } from "@tiptap/suggestion";
import { PluginKey } from "@tiptap/pm/state";

import { searchFiles, searchSkills } from "@/lib/api";
import {
  FILE_MENTION_NODE,
  type ComposerMentionItem,
  SKILL_MENTION_NODE,
} from "@/lib/composer-editor";
import type { FileMentionAttachment } from "@/lib/file-mentions";
import { displayFileMentionLabel, toAgentFileHref } from "@/lib/file-mentions";

export function composerExtensions({
  sessionUuid,
  userId,
  onSuggestionActiveChange,
}: {
  sessionUuid: string;
  userId: string;
  onSuggestionActiveChange(active: boolean): void;
}) {
  return [
    Document,
    Paragraph,
    Text,
    HardBreak,
    createMentionExtension({
      char: "@",
      className: "file-mention-pill",
      name: FILE_MENTION_NODE,
      pluginKey: "fileMentionSuggestion",
      renderLabel(label) {
        return displayFileMentionLabel(label);
      },
      async items(query) {
        const response = await searchFiles({
          userId,
          sessionUuid,
          query,
          limit: 10,
        });
        return response.matches.map((file) => ({
          id: toAgentFileHref(file.path),
          label: file.name,
          href: toAgentFileHref(file.path),
        }));
      },
      onSuggestionActiveChange,
    }),
    createMentionExtension({
      char: "$",
      className: "skill-mention-pill",
      name: SKILL_MENTION_NODE,
      pluginKey: "skillMentionSuggestion",
      renderLabel(label) {
        return label;
      },
      async items(query) {
        const response = await searchSkills({
          userId,
          sessionUuid,
          query,
          limit: 10,
        });
        return response.matches.map((skill) => ({
          id: skill.path,
          label: `$${skill.name}`,
          href: skill.path,
        }));
      },
      onSuggestionActiveChange,
    }),
  ];
}

export function insertFileMentions(
  editor: Editor | null,
  attachments: FileMentionAttachment[],
) {
  if (!editor || !attachments.length) {
    return;
  }

  const content = attachments.flatMap((attachment) => [
    {
      type: FILE_MENTION_NODE,
      attrs: {
        id: toAgentFileHref(attachment.href),
        label: attachment.label,
        mentionSuggestionChar: "@",
      },
    },
    { type: "text", text: " " },
  ]);

  editor.chain().focus().insertContent(content).run();
}

function createMentionExtension({
  char,
  className,
  name,
  pluginKey,
  renderLabel,
  items,
  onSuggestionActiveChange,
}: {
  char: "@" | "$";
  className: string;
  name: string;
  pluginKey: string;
  renderLabel(label: string): string;
  items(query: string): Promise<ComposerMentionItem[]>;
  onSuggestionActiveChange(active: boolean): void;
}) {
  return Mention.extend({ name }).configure({
    HTMLAttributes: {
      class: className,
    },
    renderText({ node }) {
      return node.attrs.label ?? node.attrs.id ?? "";
    },
    renderHTML({ options, node }) {
      return [
        "span",
        options.HTMLAttributes,
        renderLabel(node.attrs.label ?? node.attrs.id ?? ""),
      ];
    },
    suggestion: {
      char,
      pluginKey: new PluginKey(pluginKey),
      items: async ({ query }) => {
        try {
          return await items(query);
        } catch {
          return [];
        }
      },
      command({ editor, range, props }) {
        const item = props as ComposerMentionItem;
        editor
          .chain()
          .focus()
          .insertContentAt(range, [
            {
              type: name,
              attrs: {
                id: item.href,
                label: item.label,
                mentionSuggestionChar: char,
              },
            },
            { type: "text", text: " " },
          ])
          .run();
      },
      render: () =>
        createSuggestionRenderer({
          emptyText: char === "@" ? "No matching files." : "No matching skills.",
          onSuggestionActiveChange,
          renderLabel,
        }),
    },
  });
}

function createSuggestionRenderer({
  emptyText,
  onSuggestionActiveChange,
  renderLabel,
}: {
  emptyText: string;
  onSuggestionActiveChange(active: boolean): void;
  renderLabel(label: string): string;
}) {
  let root: HTMLDivElement | null = null;
  let selectedIndex = 0;
  let currentProps: SuggestionProps<ComposerMentionItem, ComposerMentionItem> | null =
    null;

  function render(props: SuggestionProps<ComposerMentionItem, ComposerMentionItem>) {
    currentProps = props;
    selectedIndex = Math.min(selectedIndex, Math.max(props.items.length - 1, 0));

    if (!root) {
      root = document.createElement("div");
      root.className =
        "fixed z-50 min-w-64 rounded-lg border bg-card p-1 shadow-[0_8px_24px_rgba(31,35,32,0.08)]";
      document.body.appendChild(root);
    }

    const rect = props.clientRect?.();
    if (rect) {
      root.style.left = `${rect.left}px`;
      root.style.top = `${rect.top - 8}px`;
      root.style.transform = "translateY(-100%)";
    }

    root.replaceChildren();
    if (!props.items.length) {
      const empty = document.createElement("div");
      empty.className = "px-3 py-2 text-sm text-muted-foreground";
      empty.textContent = emptyText;
      root.appendChild(empty);
      return;
    }

    props.items.forEach((item, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = [
        "flex w-full min-w-0 items-center rounded-md px-3 py-2 text-left text-sm",
        index === selectedIndex ? "bg-secondary" : "hover:bg-secondary",
      ].join(" ");
      button.textContent = renderLabel(item.label);
      button.onmousedown = (event) => {
        event.preventDefault();
        props.command(item);
      };
      root?.appendChild(button);
    });
  }

  function destroy() {
    root?.remove();
    root = null;
    currentProps = null;
    selectedIndex = 0;
    onSuggestionActiveChange(false);
  }

  return {
    onStart(props: SuggestionProps<ComposerMentionItem, ComposerMentionItem>) {
      selectedIndex = 0;
      onSuggestionActiveChange(true);
      render(props);
    },
    onUpdate(props: SuggestionProps<ComposerMentionItem, ComposerMentionItem>) {
      render(props);
    },
    onKeyDown({ event }: SuggestionKeyDownProps) {
      if (!currentProps?.items.length) {
        return false;
      }
      if (event.key === "ArrowDown") {
        selectedIndex = (selectedIndex + 1) % currentProps.items.length;
        render(currentProps);
        return true;
      }
      if (event.key === "ArrowUp") {
        selectedIndex =
          (selectedIndex - 1 + currentProps.items.length) %
          currentProps.items.length;
        render(currentProps);
        return true;
      }
      if (event.key === "Enter" || event.key === "Tab") {
        currentProps.command(currentProps.items[selectedIndex]);
        return true;
      }
      if (event.key === "Escape") {
        destroy();
        return true;
      }
      return false;
    },
    onExit() {
      destroy();
    },
  };
}

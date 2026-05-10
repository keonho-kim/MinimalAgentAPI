import type { DragEvent, ReactNode } from "react";

export function AppShell({
  children,
  dropActive,
  onDragLeave,
  onDragOver,
  onDrop,
  sidebar,
}: {
  children: ReactNode;
  dropActive: boolean;
  onDragLeave(event: DragEvent<HTMLElement>): void;
  onDragOver(event: DragEvent<HTMLElement>): void;
  onDrop(event: DragEvent<HTMLElement>): void;
  sidebar: ReactNode;
}) {
  return (
    <main
      className="relative flex h-dvh min-h-0 overflow-hidden bg-background text-foreground"
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {sidebar}
      {children}
      {dropActive ? (
        <div className="pointer-events-none absolute inset-0 z-20 grid place-items-center border-2 border-dashed border-ring bg-background/70 text-sm font-medium text-foreground">
          파일을 놓으면 업로드 후 첨부됩니다.
        </div>
      ) : null}
    </main>
  );
}

export function ChatPane({
  composer,
  header,
  messages,
}: {
  composer: ReactNode;
  header: ReactNode;
  messages: ReactNode;
}) {
  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
      {header}
      {messages}
      {composer}
    </section>
  );
}

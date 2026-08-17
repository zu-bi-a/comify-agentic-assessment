"use client";

import { ChatsPanel } from "./ChatsPanel";
import { TemplatesPanel } from "./TemplatesPanel";
import type { Template, Thread } from "@/lib/types";

export type SidebarTab = "chats" | "templates";

export function Sidebar({
  tab,
  onTabChange,
  threads,
  activeThreadId,
  onNewChat,
  onSelectThread,
  onRenameThread,
  onDeleteThread,
  templates,
  onEditTemplate,
}: {
  tab: SidebarTab;
  onTabChange: (tab: SidebarTab) => void;
  threads: Thread[];
  activeThreadId: string | null;
  onNewChat: () => void;
  onSelectThread: (threadId: string) => void;
  onRenameThread: (threadId: string, title: string) => void;
  onDeleteThread: (threadId: string) => void;
  templates: Template[];
  onEditTemplate: (template: Template) => void;
}) {
  return (
    <aside className="templates-pane">
      <div className="sidebar-tabs" role="tablist" aria-label="Sidebar view">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "chats"}
          className={tab === "chats" ? "active" : ""}
          onClick={() => onTabChange("chats")}
        >
          Chats
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "templates"}
          className={tab === "templates" ? "active" : ""}
          onClick={() => onTabChange("templates")}
        >
          Saved templates
        </button>
      </div>
      {tab === "chats" ? (
        <ChatsPanel
          threads={threads}
          activeThreadId={activeThreadId}
          onNew={onNewChat}
          onSelect={onSelectThread}
          onRename={onRenameThread}
          onDelete={onDeleteThread}
        />
      ) : (
        <TemplatesPanel templates={templates} onEdit={onEditTemplate} />
      )}
    </aside>
  );
}

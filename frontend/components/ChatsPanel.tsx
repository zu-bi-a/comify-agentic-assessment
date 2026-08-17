"use client";

import { KeyboardEvent, useState } from "react";
import type { Thread } from "@/lib/types";

function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function ThreadItem({
  thread,
  active,
  onSelect,
  onRename,
  onDelete,
}: {
  thread: Thread;
  active: boolean;
  onSelect: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
}) {
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState(thread.title);

  function commitRename() {
    setRenaming(false);
    const trimmed = draft.trim();
    if (trimmed && trimmed !== thread.title) onRename(trimmed);
    else setDraft(thread.title);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") commitRename();
    if (e.key === "Escape") {
      setDraft(thread.title);
      setRenaming(false);
    }
  }

  return (
    <div
      className={`chat-thread-item${active ? " active" : ""}`}
      role="button"
      tabIndex={0}
      onClick={() => !renaming && onSelect()}
      onKeyDown={(e) => e.key === "Enter" && !renaming && onSelect()}
    >
      <div className="chat-thread-main">
        {renaming ? (
          <input
            className="chat-thread-rename-input"
            value={draft}
            autoFocus
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commitRename}
            onKeyDown={handleKeyDown}
          />
        ) : (
          <span className="chat-thread-title">{thread.title}</span>
        )}
        <span className="chat-thread-meta">{formatRelativeTime(thread.updated_at)}</span>
      </div>
      <div className="chat-thread-actions">
        <button
          type="button"
          aria-label="Rename chat"
          onClick={(e) => {
            e.stopPropagation();
            setRenaming(true);
          }}
        >
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
          </svg>
        </button>
        <button
          type="button"
          aria-label="Delete chat"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
        >
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M3 6h18" />
            <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export function ChatsPanel({
  threads,
  activeThreadId,
  onNew,
  onSelect,
  onRename,
  onDelete,
}: {
  threads: Thread[];
  activeThreadId: string | null;
  onNew: () => void;
  onSelect: (threadId: string) => void;
  onRename: (threadId: string, title: string) => void;
  onDelete: (threadId: string) => void;
}) {
  return (
    <>
      <button type="button" className="new-chat-button" onClick={onNew}>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        New chat
      </button>
      {threads.length === 0 ? (
        <div className="empty-state">No chats yet.</div>
      ) : (
        threads.map((t) => (
          <ThreadItem
            key={t.id}
            thread={t}
            active={t.id === activeThreadId}
            onSelect={() => onSelect(t.id)}
            onRename={(title) => onRename(t.id, title)}
            onDelete={() => onDelete(t.id)}
          />
        ))
      )}
    </>
  );
}

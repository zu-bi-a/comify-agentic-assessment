"use client";

import { useEffect, useRef, useState } from "react";
import { ChatHeader } from "@/components/ChatHeader";
import { Composer } from "@/components/Composer";
import { MessageBubble } from "@/components/MessageBubble";
import { QuickReplies } from "@/components/QuickReplies";
import { Sidebar, SidebarTab } from "@/components/Sidebar";
import { TypingIndicator } from "@/components/TypingIndicator";
import {
  deleteThread,
  fetchTemplates,
  fetchThreadMessages,
  fetchThreads,
  renameThread,
  sendChatMessage,
} from "@/lib/api";
import type { AgentHint, ChatMessage, Template, Thread } from "@/lib/types";

const THREAD_STORAGE_KEY = "giva_active_thread_id";

const GREETING_TEXT =
  "Hi! I can help you create a WhatsApp Business template or a push notification for Giva. What would you like to build?";
const GREETING_QUICK_REPLIES = ["WhatsApp template", "Push notification"];

function greeting(): ChatMessage {
  return {
    id: crypto.randomUUID(),
    role: "agent",
    text: GREETING_TEXT,
    quickReplies: GREETING_QUICK_REPLIES,
  };
}

export default function Home() {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>("chats");
  const [agentName, setAgentName] = useState("Triage Agent");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      const list = await fetchThreads().catch(() => []);
      setThreads(list);
      const savedId = localStorage.getItem(THREAD_STORAGE_KEY);
      const match = savedId ? list.find((t) => t.id === savedId) : undefined;
      if (match) {
        await openThread(match);
      } else {
        resetToNewChat();
      }
      setLoading(false);
    })();
    refreshTemplates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function refreshTemplates() {
    try {
      setTemplates(await fetchTemplates());
    } catch {
      // non-fatal
    }
  }

  async function refreshThreads() {
    try {
      setThreads(await fetchThreads());
    } catch {
      // non-fatal
    }
  }

  function resetToNewChat() {
    setActiveThreadId(null);
    setAgentName("Triage Agent");
    setMessages([greeting()]);
    localStorage.removeItem(THREAD_STORAGE_KEY);
  }

  async function openThread(thread: Thread) {
    setLoading(true);
    try {
      const history = await fetchThreadMessages(thread.id);
      setMessages(
        history.map((m) => ({
          id: m.id,
          role: m.role,
          text: m.text,
          quickReplies: m.quick_replies ?? undefined,
        }))
      );
      setActiveThreadId(thread.id);
      setAgentName(thread.agent_name);
      localStorage.setItem(THREAD_STORAGE_KEY, thread.id);
    } catch {
      resetToNewChat();
    } finally {
      setLoading(false);
    }
  }

  async function sendToAgent(
    text: string,
    options?: { agentHint?: AgentHint; showUserMessage?: boolean; threadId?: string | null }
  ) {
    const requestThreadId = options?.threadId !== undefined ? options.threadId : activeThreadId;
    if (options?.showUserMessage ?? true) {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text }]);
    }
    setSending(true);
    try {
      const res = await sendChatMessage(requestThreadId, text, options?.agentHint);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "agent",
          text: res.reply,
          quickReplies: res.quick_replies ?? undefined,
        },
      ]);
      setAgentName(res.agent);
      setActiveThreadId(res.thread_id);
      localStorage.setItem(THREAD_STORAGE_KEY, res.thread_id);
      await Promise.all([refreshTemplates(), refreshThreads()]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "system",
          text: `Network error: ${err instanceof Error ? err.message : String(err)}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  function handleSend(text: string) {
    return sendToAgent(text);
  }

  function handleEditTemplate(template: Template) {
    setActiveThreadId(null);
    setAgentName("Triage Agent");
    setMessages([]);
    localStorage.removeItem(THREAD_STORAGE_KEY);
    setSidebarTab("chats");
    return sendToAgent(`[EDIT_TEMPLATE] id=${template.id}`, {
      agentHint: template.channel as AgentHint,
      showUserMessage: false,
      threadId: null,
    });
  }

  function handleNewChat() {
    if (sending) return;
    resetToNewChat();
  }

  function handleSelectThread(threadId: string) {
    if (sending || threadId === activeThreadId) return;
    const thread = threads.find((t) => t.id === threadId);
    if (thread) openThread(thread);
  }

  async function handleRenameThread(threadId: string, title: string) {
    try {
      await renameThread(threadId, title);
      await refreshThreads();
    } catch {
      // non-fatal
    }
  }

  async function handleDeleteThread(threadId: string) {
    if (sending) return;
    if (!window.confirm("Delete this chat? This can't be undone.")) return;
    try {
      await deleteThread(threadId);
      await refreshThreads();
      if (threadId === activeThreadId) resetToNewChat();
    } catch {
      // non-fatal
    }
  }

  const lastMessage = messages[messages.length - 1];
  const showQuickReplies =
    !sending && !loading && lastMessage?.role === "agent" && (lastMessage.quickReplies?.length ?? 0) > 0;

  return (
    <div className="layout">
      <main className="chat-pane">
        <ChatHeader agentName={agentName} />
        <div className="messages">
          {messages.map((m, i) => (
            <MessageBubble key={m.id} message={m} showAvatar={messages[i - 1]?.role !== m.role} />
          ))}
          {showQuickReplies && (
            <div className="quick-replies-row">
              <div className="msg-avatar-slot" />
              <QuickReplies
                options={lastMessage.quickReplies!}
                disabled={sending}
                onPick={handleSend}
              />
            </div>
          )}
          {sending && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
        <Composer disabled={sending || loading} onSend={handleSend} />
      </main>
      <Sidebar
        tab={sidebarTab}
        onTabChange={setSidebarTab}
        threads={threads}
        activeThreadId={activeThreadId}
        onNewChat={handleNewChat}
        onSelectThread={handleSelectThread}
        onRenameThread={handleRenameThread}
        onDeleteThread={handleDeleteThread}
        templates={templates}
        onEditTemplate={handleEditTemplate}
      />
    </div>
  );
}

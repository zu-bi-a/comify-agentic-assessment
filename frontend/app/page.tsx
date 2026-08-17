"use client";

import { useEffect, useRef, useState } from "react";
import { ChatHeader } from "@/components/ChatHeader";
import { Composer } from "@/components/Composer";
import { MessageBubble } from "@/components/MessageBubble";
import { QuickReplies } from "@/components/QuickReplies";
import { TemplatesSidebar } from "@/components/TemplatesSidebar";
import { TypingIndicator } from "@/components/TypingIndicator";
import { fetchTemplates, sendChatMessage } from "@/lib/api";
import type { AgentHint, ChatMessage, Template } from "@/lib/types";

const SESSION_STORAGE_KEY = "giva_session_id";

function getOrCreateSessionId(): string {
  const existing = localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;
  const id = crypto.randomUUID();
  localStorage.setItem(SESSION_STORAGE_KEY, id);
  return id;
}

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [agentName, setAgentName] = useState("Triage Agent");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(getOrCreateSessionId());
    setMessages([
      {
        id: crypto.randomUUID(),
        role: "agent",
        text: "Hi! I can help you create a WhatsApp Business template or a push notification for Giva. What would you like to build?",
        quickReplies: ["WhatsApp template", "Push notification"],
      },
    ]);
    refreshTemplates();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function refreshTemplates() {
    try {
      const data = await fetchTemplates();
      setTemplates(data);
    } catch {
      // non-fatal
    }
  }

  async function sendToAgent(
    text: string,
    options?: { agentHint?: AgentHint; showUserMessage?: boolean }
  ) {
    if (!sessionId) return;
    if (options?.showUserMessage ?? true) {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text }]);
    }
    setSending(true);
    try {
      const res = await sendChatMessage(sessionId, text, options?.agentHint);
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
      await refreshTemplates();
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
    return sendToAgent(`[EDIT_TEMPLATE] id=${template.id}`, {
      agentHint: template.channel as AgentHint,
      showUserMessage: false,
    });
  }

  const lastMessage = messages[messages.length - 1];
  const showQuickReplies =
    !sending && lastMessage?.role === "agent" && (lastMessage.quickReplies?.length ?? 0) > 0;

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
        <Composer disabled={!sessionId || sending} onSend={handleSend} />
      </main>
      <TemplatesSidebar templates={templates} onEdit={handleEditTemplate} />
    </div>
  );
}

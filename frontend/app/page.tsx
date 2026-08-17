"use client";

import { useEffect, useRef, useState } from "react";
import { ChatHeader } from "@/components/ChatHeader";
import { Composer } from "@/components/Composer";
import { MessageBubble } from "@/components/MessageBubble";
import { TemplatesSidebar } from "@/components/TemplatesSidebar";
import { fetchTemplates, sendChatMessage } from "@/lib/api";
import type { ChatMessage, Template } from "@/lib/types";

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
      },
    ]);
    refreshTemplates();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function refreshTemplates() {
    try {
      const data = await fetchTemplates();
      setTemplates(data);
    } catch {
      // non-fatal
    }
  }

  async function handleSend(text: string) {
    if (!sessionId) return;
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text }]);
    setSending(true);
    try {
      const res = await sendChatMessage(sessionId, text);
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "agent", text: res.reply },
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

  return (
    <div className="layout">
      <main className="chat-pane">
        <ChatHeader agentName={agentName} />
        <div className="messages">
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          <div ref={messagesEndRef} />
        </div>
        <Composer disabled={!sessionId || sending} onSend={handleSend} />
      </main>
      <TemplatesSidebar templates={templates} />
    </div>
  );
}

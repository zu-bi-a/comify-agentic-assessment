import type { ChatResponse, Template } from "./types";

export async function sendChatMessage(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTemplates(channel?: string): Promise<Template[]> {
  const url = channel
    ? `/api/templates?channel=${encodeURIComponent(channel)}`
    : "/api/templates";
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Templates request failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

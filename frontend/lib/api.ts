import type { AgentHint, ChatResponse, Template, Thread, ThreadMessage } from "./types";

async function unwrap<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    throw new Error(`${label} failed: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function sendChatMessage(
  threadId: string | null,
  message: string,
  agentHint?: AgentHint
): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message, agent_hint: agentHint }),
  });
  return unwrap(res, "Chat request");
}

export async function fetchTemplates(channel?: string): Promise<Template[]> {
  const url = channel
    ? `/api/templates?channel=${encodeURIComponent(channel)}`
    : "/api/templates";
  const res = await fetch(url);
  return unwrap(res, "Templates request");
}

export async function fetchThreads(): Promise<Thread[]> {
  const res = await fetch("/api/threads");
  return unwrap(res, "Threads request");
}

export async function fetchThreadMessages(threadId: string): Promise<ThreadMessage[]> {
  const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}/messages`);
  return unwrap(res, "Thread messages request");
}

export async function renameThread(threadId: string, title: string): Promise<Thread> {
  const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return unwrap(res, "Rename thread request");
}

export async function deleteThread(threadId: string): Promise<void> {
  const res = await fetch(`/api/threads/${encodeURIComponent(threadId)}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`Delete thread failed: ${res.status} ${res.statusText}`);
  }
}

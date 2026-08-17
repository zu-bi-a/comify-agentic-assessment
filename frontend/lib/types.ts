export type MessageRole = "user" | "agent" | "system";

export type AgentHint = "whatsapp" | "push";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  quickReplies?: string[];
}

export interface ChatResponse {
  thread_id: string;
  reply: string;
  agent: string;
  quick_replies?: string[] | null;
}

export interface Thread {
  id: string;
  title: string;
  agent_name: string;
  created_at: string;
  updated_at: string;
}

export interface ThreadMessage {
  id: string;
  thread_id: string;
  role: "user" | "agent";
  text: string;
  quick_replies?: string[] | null;
  created_at: string;
}

export interface Template {
  id: string;
  channel: string;
  name: string;
  brand: string;
  payload: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at?: string;
}

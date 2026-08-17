export type MessageRole = "user" | "agent" | "system";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  quickReplies?: string[];
}

export interface ChatResponse {
  reply: string;
  agent: string;
  quick_replies?: string[] | null;
}

export interface Template {
  id: string;
  channel: string;
  name: string;
  brand: string;
  payload: Record<string, unknown>;
  status: string;
  created_at: string;
}

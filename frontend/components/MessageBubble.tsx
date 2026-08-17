import type { ChatMessage } from "@/lib/types";

export function MessageBubble({ message }: { message: ChatMessage }) {
  return <div className={`msg ${message.role}`}>{message.text}</div>;
}

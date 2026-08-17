import type { ChatMessage } from "@/lib/types";
import { Avatar } from "./Avatar";

export function MessageBubble({
  message,
  showAvatar,
}: {
  message: ChatMessage;
  showAvatar: boolean;
}) {
  return (
    <div className={`msg-row ${message.role}`}>
      <div className="msg-avatar-slot">{showAvatar && <Avatar role={message.role} />}</div>
      <div className={`msg ${message.role}`}>{message.text}</div>
    </div>
  );
}

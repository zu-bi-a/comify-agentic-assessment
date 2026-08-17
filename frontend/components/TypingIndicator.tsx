import { Avatar } from "./Avatar";

export function TypingIndicator() {
  return (
    <div className="msg-row agent" role="status" aria-live="polite">
      <div className="msg-avatar-slot">
        <Avatar role="agent" />
      </div>
      <div className="msg agent typing-bubble">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="sr-only">Agent is typing…</span>
      </div>
    </div>
  );
}

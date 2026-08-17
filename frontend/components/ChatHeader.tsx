export function ChatHeader({ agentName }: { agentName: string }) {
  return (
    <header className="chat-header">
      <div className="brand">Giva Template Studio</div>
      <div className="agent-badge">{agentName}</div>
    </header>
  );
}

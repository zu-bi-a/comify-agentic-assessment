function agentTone(agentName: string): "whatsapp" | "push" | "triage" {
  if (agentName.toLowerCase().includes("whatsapp")) return "whatsapp";
  if (agentName.toLowerCase().includes("push")) return "push";
  return "triage";
}

export function ChatHeader({ agentName }: { agentName: string }) {
  return (
    <header className="chat-header">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          G
        </span>
        <div className="brand-text">
          <span className="brand-name">Giva Template Studio</span>
          <span className="brand-subtitle">AI template assistant</span>
        </div>
      </div>
      <div className={`agent-badge agent-badge-${agentTone(agentName)}`}>
        <span className="agent-badge-dot" aria-hidden="true" />
        {agentName}
      </div>
    </header>
  );
}

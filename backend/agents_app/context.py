from dataclasses import dataclass, field


@dataclass
class GivaContext:
    """Run context shared across all agents, tools, and guardrails for one chat session."""

    brand_name: str = "Giva"
    session_id: str = ""
    # In-progress template draft, carried across handoffs (e.g. WhatsApp -> Push).
    draft: dict = field(default_factory=dict)

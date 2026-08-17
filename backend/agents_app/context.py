from dataclasses import dataclass, field


@dataclass
class GivaContext:
    """Run context shared across all agents, tools, and guardrails for one chat session."""

    brand_name: str = "Giva"
    session_id: str = ""
    # In-progress template draft, carried across handoffs (e.g. WhatsApp -> Push).
    draft: dict = field(default_factory=dict)
    # Quick-reply chip labels for the current turn, set via the
    # offer_quick_replies tool and read/cleared by the API layer each turn.
    pending_quick_replies: list[str] | None = None
    # Set by load_template_for_editing when the user is revising a saved
    # template; tells the agent to update this id instead of saving a new one.
    editing_template_id: str | None = None
    # Auto-captured by find_catalogue_collection on a confident match, so
    # save/find_similar_templates can auto-tag with it without relying on the
    # agent remembering to pass it explicitly.
    confirmed_collection: str | None = None

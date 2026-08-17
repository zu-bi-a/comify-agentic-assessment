from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT_DIR / ".env")

from agents import (  # noqa: E402
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    Runner,
    SQLiteSession,
)
from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from agents_app import store  # noqa: E402
from agents_app.agents_def import (  # noqa: E402
    AGENTS_BY_NAME,
    push_agent,
    triage_agent,
    whatsapp_agent,
)
from agents_app.context import GivaContext  # noqa: E402

AGENT_HINTS = {"whatsapp": whatsapp_agent, "push": push_agent}

DATA_DIR = Path(os.environ.get("GIVA_DATA_DIR", str(ROOT_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATIONS_DB = str(DATA_DIR / "conversations.db")

app = FastAPI(title="Giva Template Studio")

# session_id -> {"agent_name": str, "context": GivaContext}
_SESSION_STATE: dict[str, dict] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    agent_hint: str | None = None


class ChatResponse(BaseModel):
    reply: str
    agent: str
    quick_replies: list[str] | None = None


def _get_session_state(session_id: str) -> dict:
    if session_id not in _SESSION_STATE:
        _SESSION_STATE[session_id] = {
            "agent_name": triage_agent.name,
            "context": GivaContext(session_id=session_id),
        }
    return _SESSION_STATE[session_id]


GENERIC_COMPLIANCE_REVISION_PROMPT = (
    "Your previous draft did not pass Giva's brand compliance review. Revise it "
    "so it fully complies with the brand guardrails (no false material claims "
    "like implying gold/diamond for a silver piece, no fake urgency or scarcity "
    "unless the user gave a real offer, no health/luck/spiritual/financial "
    "benefit claims, no invented discounts or prices, no competitor mentions, "
    "no phishing or account-scare language) and present the corrected draft."
)


def _pop_quick_replies(context: GivaContext) -> list[str] | None:
    quick_replies = context.pending_quick_replies
    context.pending_quick_replies = None
    return quick_replies


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    state = _get_session_state(req.session_id)
    if req.agent_hint and req.agent_hint in AGENT_HINTS:
        current_agent = AGENT_HINTS[req.agent_hint]
    else:
        current_agent = AGENTS_BY_NAME.get(state["agent_name"], triage_agent)
    session = SQLiteSession(req.session_id, CONVERSATIONS_DB)
    state["context"].pending_quick_replies = None

    try:
        result = await Runner.run(
            current_agent, req.message, context=state["context"], session=session
        )
    except InputGuardrailTripwireTriggered:
        _pop_quick_replies(state["context"])
        return ChatResponse(
            reply=(
                "I can't help with that request — it looks like it's asking for "
                "content outside what I'm allowed to generate (e.g. impersonation, "
                "phishing-style language, or something unrelated to Giva WhatsApp/"
                "push templates). Try rephrasing what you'd like the template to say."
            ),
            agent=current_agent.name,
        )
    except OutputGuardrailTripwireTriggered:
        try:
            retry_result = await Runner.run(
                current_agent,
                GENERIC_COMPLIANCE_REVISION_PROMPT,
                context=state["context"],
                session=session,
            )
            state["agent_name"] = retry_result.last_agent.name
            return ChatResponse(
                reply=retry_result.final_output,
                agent=retry_result.last_agent.name,
                quick_replies=_pop_quick_replies(state["context"]),
            )
        except (InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered):
            _pop_quick_replies(state["context"])
            return ChatResponse(
                reply=(
                    "That draft didn't pass brand compliance and I wasn't able to "
                    "auto-revise it. Could you rephrase the request without any "
                    "claims about gold/diamond materials, guaranteed offers, or "
                    "urgency language?"
                ),
                agent=current_agent.name,
            )

    state["agent_name"] = result.last_agent.name
    return ChatResponse(
        reply=result.final_output,
        agent=result.last_agent.name,
        quick_replies=_pop_quick_replies(state["context"]),
    )


@app.get("/templates")
async def list_templates(channel: str | None = None) -> list[dict]:
    return store.list_templates(channel)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

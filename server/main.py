from __future__ import annotations

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
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from agents_app import store  # noqa: E402
from agents_app.agents_def import AGENTS_BY_NAME, triage_agent  # noqa: E402
from agents_app.context import GivaContext  # noqa: E402

DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONVERSATIONS_DB = str(DATA_DIR / "conversations.db")

app = FastAPI(title="Giva Template Studio")

# session_id -> {"agent_name": str, "context": GivaContext}
_SESSION_STATE: dict[str, dict] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    agent: str


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


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    state = _get_session_state(req.session_id)
    current_agent = AGENTS_BY_NAME.get(state["agent_name"], triage_agent)
    session = SQLiteSession(req.session_id, CONVERSATIONS_DB)

    try:
        result = await Runner.run(
            current_agent, req.message, context=state["context"], session=session
        )
    except InputGuardrailTripwireTriggered:
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
                reply=retry_result.final_output, agent=retry_result.last_agent.name
            )
        except (InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered):
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
    return ChatResponse(reply=result.final_output, agent=result.last_agent.name)


@app.get("/templates")
async def list_templates(channel: str | None = None) -> list[dict]:
    return store.list_templates(channel)


app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(str(Path(__file__).parent / "static" / "index.html"))

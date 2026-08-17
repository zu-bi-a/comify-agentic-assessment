from __future__ import annotations

import sys
from contextlib import asynccontextmanager
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
)
from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from agents_app import db, store, threads  # noqa: E402
from agents_app.agents_def import (  # noqa: E402
    AGENTS_BY_NAME,
    push_agent,
    triage_agent,
    whatsapp_agent,
)
from agents_app.context import GivaContext  # noqa: E402

AGENT_HINTS = {"whatsapp": whatsapp_agent, "push": push_agent}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_models()
    yield


app = FastAPI(title="Giva Template Studio", lifespan=lifespan)

# thread_id -> {"agent_name": str, "context": GivaContext} -- in-process cache of
# per-thread agent state; the durable record lives in the `threads` table.
_SESSION_STATE: dict[str, dict] = {}


class ChatRequest(BaseModel):
    thread_id: str | None = None
    message: str
    agent_hint: str | None = None


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    agent: str
    quick_replies: list[str] | None = None


class RenameThreadRequest(BaseModel):
    title: str


async def _get_session_state(thread_id: str, agent_name: str) -> dict:
    if thread_id not in _SESSION_STATE:
        _SESSION_STATE[thread_id] = {
            "agent_name": agent_name,
            "context": GivaContext(session_id=thread_id),
        }
    return _SESSION_STATE[thread_id]


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
    is_new_thread = req.thread_id is None
    if is_new_thread:
        thread_row = await threads.create_thread()
    else:
        thread_row = await threads.get_thread(req.thread_id)
        if thread_row is None:
            raise HTTPException(status_code=404, detail="Thread not found")
    thread_id = thread_row["id"]
    title_on_first_message = threads.derive_title(req.message) if is_new_thread else None

    state = await _get_session_state(thread_id, thread_row["agent_name"])
    if req.agent_hint and req.agent_hint in AGENT_HINTS:
        current_agent = AGENT_HINTS[req.agent_hint]
    else:
        current_agent = AGENTS_BY_NAME.get(state["agent_name"], triage_agent)
    session = db.agent_session(thread_id)
    state["context"].pending_quick_replies = None

    async def _finish(reply: str, agent_name: str, quick_replies: list[str] | None) -> ChatResponse:
        await threads.add_message(thread_id, "user", req.message)
        await threads.add_message(thread_id, "agent", reply, quick_replies)
        await threads.touch_thread(thread_id, agent_name=agent_name, title=title_on_first_message)
        state["agent_name"] = agent_name
        return ChatResponse(thread_id=thread_id, reply=reply, agent=agent_name, quick_replies=quick_replies)

    try:
        result = await Runner.run(
            current_agent, req.message, context=state["context"], session=session
        )
    except InputGuardrailTripwireTriggered:
        _pop_quick_replies(state["context"])
        return await _finish(
            (
                "I can't help with that request — it looks like it's asking for "
                "content outside what I'm allowed to generate (e.g. impersonation, "
                "phishing-style language, or something unrelated to Giva WhatsApp/"
                "push templates). Try rephrasing what you'd like the template to say."
            ),
            current_agent.name,
            None,
        )
    except OutputGuardrailTripwireTriggered:
        try:
            retry_result = await Runner.run(
                current_agent,
                GENERIC_COMPLIANCE_REVISION_PROMPT,
                context=state["context"],
                session=session,
            )
            return await _finish(
                retry_result.final_output,
                retry_result.last_agent.name,
                _pop_quick_replies(state["context"]),
            )
        except (InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered):
            _pop_quick_replies(state["context"])
            return await _finish(
                (
                    "That draft didn't pass brand compliance and I wasn't able to "
                    "auto-revise it. Could you rephrase the request without any "
                    "claims about gold/diamond materials, guaranteed offers, or "
                    "urgency language?"
                ),
                current_agent.name,
                None,
            )

    return await _finish(
        result.final_output, result.last_agent.name, _pop_quick_replies(state["context"])
    )


@app.get("/threads")
async def list_threads() -> list[dict]:
    return await threads.list_threads()


@app.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str) -> list[dict]:
    thread_row = await threads.get_thread(thread_id)
    if thread_row is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return await threads.list_messages(thread_id)


@app.patch("/threads/{thread_id}")
async def rename_thread(thread_id: str, req: RenameThreadRequest) -> dict:
    record = await threads.rename_thread(thread_id, req.title)
    if record is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return record


@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict:
    await db.agent_session(thread_id).clear_session()
    deleted = await threads.delete_thread(thread_id)
    _SESSION_STATE.pop(thread_id, None)
    if not deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"status": "deleted"}


@app.get("/templates")
async def list_templates(channel: str | None = None) -> list[dict]:
    return await store.list_templates(channel)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

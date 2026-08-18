from __future__ import annotations

import os
from contextlib import nullcontext
from typing import Any

from agents import Agent, RunResult, Runner
from agents.memory import Session

_enabled = False
_langfuse: Any = None


def setup_observability() -> None:
    """Wires the OpenAI Agents SDK into Langfuse via OpenInference, if a
    Langfuse project is configured. No-op (and safe to run without the
    Langfuse stack up) when LANGFUSE_PUBLIC_KEY is unset -- tracing is
    opt-in for local debugging, not required to run the app."""
    global _enabled, _langfuse
    if not os.environ.get("LANGFUSE_PUBLIC_KEY"):
        return

    from langfuse import get_client
    from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor

    _langfuse = get_client()
    OpenAIAgentsInstrumentor().instrument()
    _enabled = True


async def traced_run(
    agent: Agent,
    input: str,
    *,
    context: Any,
    session: Session,
    thread_id: str,
    metadata: dict[str, Any],
) -> RunResult:
    """Runner.run wrapped with Langfuse session/metadata, when observability
    is enabled. `thread_id` becomes the Langfuse session_id, so every turn of
    a conversation groups into one Session in the UI -- the point being to
    go from "a trace" to "this whole conversation, in order."""
    if not _enabled:
        return await Runner.run(agent, input, context=context, session=session)

    from langfuse import propagate_attributes

    with _langfuse.start_as_current_observation(name=f"chat_turn:{agent.name}") as span:
        with propagate_attributes(
            session_id=thread_id,
            tags=[metadata.get("turn_kind", "primary")],
            metadata=metadata,
        ):
            result = await Runner.run(agent, input, context=context, session=session)
        span.update(input=input, output=result.final_output)
    return result


def observability_span(name: str, data: dict[str, Any] | None = None):
    """Wraps agents.custom_span when observability is enabled, else a no-op
    context manager -- lets call sites always wrap business-decision points
    without checking `_enabled` themselves."""
    if not _enabled:
        return nullcontext()
    from agents import custom_span

    return custom_span(name, data=data or {})


def eval_trace(name: str, metadata: dict[str, Any] | None = None):
    """Root span for one eval case run, tagged distinctly from production chat
    turns (see traced_run) so eval runs and live traffic are both visible in
    Langfuse but easy to tell apart. No-op when observability is disabled."""
    if not _enabled:
        return nullcontext()
    return _langfuse.start_as_current_observation(name=name, metadata=metadata or {})


def score_current_trace(name: str, passed: bool, comment: str) -> None:
    """Attaches a pass/fail score to the currently-open Langfuse trace (an eval
    case's trace, opened via eval_trace). No-op when observability is disabled."""
    if not _enabled:
        return
    _langfuse.score_current_trace(
        name=name, value=1.0 if passed else 0.0, data_type="BOOLEAN", comment=comment[:500]
    )

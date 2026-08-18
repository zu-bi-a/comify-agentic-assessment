from __future__ import annotations

from typing import Any

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
)
from pydantic import BaseModel

from .context import GivaContext
from .tools import get_brand_guidelines


class SafetyCheckOutput(BaseModel):
    is_unsafe: bool
    reason: str


intent_safety_guardrail_agent = Agent(
    name="Intent Safety Check",
    instructions=(
        "You screen incoming requests to a Giva marketing-template assistant. "
        "This assistant creates/edits WhatsApp and push templates for the "
        "Giva jewelry brand, AND answers questions about its own "
        "capabilities, Giva's product catalogue, brainstorming template "
        "ideas, and looking up previously saved templates -- all of that is "
        "in scope, not just literal template drafting. Flag is_unsafe=true "
        "only for requests that ask to: impersonate a bank, government body, "
        "or delivery/security service; write phishing or OTP-scam language; "
        "produce hateful, adult, or illegal content; attack or name a "
        "competitor; or that are entirely unrelated to this assistant and its "
        "scope above (e.g. general trivia, coding help, unrelated topics). "
        "Ordinary requests to draft, revise, or discuss WhatsApp/push "
        "templates, ask what this assistant can or can't do, ask about the "
        "catalogue, ask for template ideas, or ask whether a template already "
        "exists -- including ones that mention discounts, occasions, or "
        "product details -- are safe (is_unsafe=false). When in doubt, prefer "
        "is_unsafe=false and let the specialist/general agent and "
        "brand-compliance check handle content quality."
    ),
    output_type=SafetyCheckOutput,
)


@input_guardrail
async def intent_safety_guardrail(
    ctx: RunContextWrapper[GivaContext],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Blocks scam/impersonation/off-topic requests before any specialist agent runs."""
    result = await Runner.run(intent_safety_guardrail_agent, input, context=ctx.context)
    output = result.final_output
    return GuardrailFunctionOutput(
        output_info=output,
        tripwire_triggered=output.is_unsafe,
    )


class ComplianceCheckOutput(BaseModel):
    is_compliant: bool
    violations: list[str]


brand_compliance_guardrail_agent = Agent(
    name="Brand Compliance Check",
    instructions=(
        "You review a drafted Giva template against brand guardrails before it "
        "is shown to the user as final. Call get_brand_guidelines(section="
        "'guardrails') to read the current rules. Set is_compliant=false ONLY "
        "for HARD violations: false material claims (implying gold/diamond for "
        "silver items), fake urgency/scarcity not sourced from the user, "
        "health/luck/spiritual/financial benefit claims, invented discounts or "
        "prices, competitor mentions, or phishing/account-scare language. Minor "
        "style nitpicks are NOT violations -- leave those to the drafting "
        "agent. List every hard violation found in 'violations'; leave it "
        "empty if compliant."
    ),
    tools=[get_brand_guidelines],
    output_type=ComplianceCheckOutput,
)


@output_guardrail
async def brand_compliance_guardrail(
    ctx: RunContextWrapper[GivaContext],
    agent: Agent,
    output: Any,
) -> GuardrailFunctionOutput:
    """Catches hard brand-guardrail violations in a drafted template before it reaches the user."""
    result = await Runner.run(
        brand_compliance_guardrail_agent,
        f"Review this drafted template output for brand-guardrail violations:\n\n{output}",
        context=ctx.context,
    )
    check = result.final_output
    return GuardrailFunctionOutput(
        output_info=check,
        tripwire_triggered=not check.is_compliant,
    )

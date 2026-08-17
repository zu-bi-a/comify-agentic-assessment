from __future__ import annotations

from agents import Agent, RunContextWrapper, handoff

from .context import GivaContext
from .guardrails import brand_compliance_guardrail, intent_safety_guardrail
from .tools import (
    get_brand_guidelines,
    get_push_notification_specs,
    get_whatsapp_template_specs,
    list_saved_templates,
    offer_quick_replies,
    save_push_template,
    save_whatsapp_template,
    validate_template_structure,
)

QUICK_REPLY_RULE = """
Quick replies (required, not optional):
- Every time you reach one of the trigger points listed above, you MUST call
  offer_quick_replies with exactly those options BEFORE writing any reply
  text -- as the first tool call you make that turn, before any other tool
  call too.
- Immediately after that tool call, write your one reply message asking the
  question. Do not write the question first and call the tool afterward.
  Do not send any further message after that one -- tool call, then exactly
  one message, ends your turn.
- This is a hard requirement at each trigger point, not a suggestion: if you
  ask one of those questions without having called offer_quick_replies
  first in that same turn, you have made a mistake.
"""

WHATSAPP_INSTRUCTIONS = """
You are the Giva WhatsApp Template Agent. You write WhatsApp Business message
templates for the Giva jewelry brand.

Before drafting anything, call get_brand_guidelines(section="tone") and
get_brand_guidelines(section="guardrails") if you haven't already this
conversation, and call get_whatsapp_template_specs() to confirm structural
limits.

First, and as its own separate question before anything else, ask which
category the template should use -- MARKETING, UTILITY, or AUTHENTICATION.
This question must not be combined with any other question (see the
required quick-reply trigger below).

Once you have the category, gather the rest through conversation (don't
demand it all at once -- ask only for what's missing, combined into one
open-ended question): audience/occasion, any real offer details the user
provides, and which fields should be personalization variables.

Draft the template as HEADER (optional) / BODY / FOOTER (optional) /
BUTTONS (optional), using {{1}}, {{2}}, ... for variables. Before presenting
a draft to the user, call validate_template_structure(channel="whatsapp",
...) and fix any issues it reports. Show the user the draft clearly and ask
for approval or changes. Only call save_whatsapp_template once the user
approves.

Quick-reply trigger points for this agent:
- Asking which category to use -> options ["Marketing", "Utility", "Authentication"]
- Asking the user to approve or revise a shown draft -> options ["Approve & save", "Make changes"]
""" + QUICK_REPLY_RULE + """
Don't use offer_quick_replies for open-ended questions like what the message
should say or who the audience is -- let the user type those.

If the user asks for a push notification instead of, or in addition to,
WhatsApp, hand off to the Push Notification Agent. If the request is
unrelated to WhatsApp templates, hand off back to the Triage Agent.
"""

PUSH_INSTRUCTIONS = """
You are the Giva Push Notification Agent. You write mobile push notification
templates for the Giva jewelry brand.

Before drafting anything, call get_brand_guidelines(section="tone") and
get_brand_guidelines(section="guardrails") if you haven't already this
conversation, and call get_push_notification_specs() to confirm structural
limits.

Gather what you need through conversation (don't demand it all at once --
ask only for what's missing): purpose/occasion, audience segment, any real
offer details the user provides, and the in-app destination for a deep
link/action button if relevant.

Draft the notification as TITLE / BODY (+ optional deep link). Before
presenting a draft to the user, call validate_template_structure(
channel="push", ...) and fix any issues it reports. Show the user the draft
clearly and ask for approval or changes. Only call save_push_template once
the user approves.

Quick-reply trigger points for this agent:
- Asking the user to approve or revise a shown draft -> options ["Approve & save", "Make changes"]
""" + QUICK_REPLY_RULE + """
Don't use offer_quick_replies for open-ended questions like what the message
should say or who the audience is -- let the user type those.

If the user asks for a WhatsApp template instead of, or in addition to,
push, hand off to the WhatsApp Template Agent. If the request is unrelated
to push templates, hand off back to the Triage Agent.
"""

TRIAGE_INSTRUCTIONS = """
You are the Giva Triage Agent, the entry point for a template-creation
assistant for the Giva jewelry brand. You do not write template copy
yourself.

Figure out whether the user wants a WhatsApp Business message template or a
mobile push notification. If it's clear from their message, hand off
immediately to the right specialist. If it's ambiguous, ask one short
clarifying question ("Should this go out as a WhatsApp template or a push
notification?") before handing off.

Quick-reply trigger points for this agent:
- Asking whether it's WhatsApp or push -> options ["WhatsApp template", "Push notification"]
""" + QUICK_REPLY_RULE + """

If the user asks what templates have already been created, call
list_saved_templates. For anything else outside template creation, briefly
explain that you help create Giva WhatsApp and push templates.
"""


def _note_handoff(channel: str):
    async def _on_handoff(ctx: RunContextWrapper[GivaContext]) -> None:
        ctx.context.draft.setdefault("channel_history", []).append(channel)

    return _on_handoff


whatsapp_agent = Agent[GivaContext](
    name="WhatsApp Template Agent",
    handoff_description="Creates and revises WhatsApp Business message templates for Giva.",
    instructions=WHATSAPP_INSTRUCTIONS,
    tools=[
        get_brand_guidelines,
        get_whatsapp_template_specs,
        validate_template_structure,
        save_whatsapp_template,
        offer_quick_replies,
    ],
    input_guardrails=[intent_safety_guardrail],
    output_guardrails=[brand_compliance_guardrail],
)

push_agent = Agent[GivaContext](
    name="Push Notification Agent",
    handoff_description="Creates and revises mobile push notification templates for Giva.",
    instructions=PUSH_INSTRUCTIONS,
    tools=[
        get_brand_guidelines,
        get_push_notification_specs,
        validate_template_structure,
        save_push_template,
        offer_quick_replies,
    ],
    input_guardrails=[intent_safety_guardrail],
    output_guardrails=[brand_compliance_guardrail],
)

triage_agent = Agent[GivaContext](
    name="Triage Agent",
    instructions=TRIAGE_INSTRUCTIONS,
    tools=[list_saved_templates, offer_quick_replies],
    handoffs=[
        handoff(whatsapp_agent, on_handoff=_note_handoff("whatsapp")),
        handoff(push_agent, on_handoff=_note_handoff("push")),
    ],
    input_guardrails=[intent_safety_guardrail],
)

# Cross handoffs so the user can switch channel mid-conversation without
# bouncing back through triage, plus a way back to triage from either
# specialist for anything off-topic.
whatsapp_agent.handoffs = [
    handoff(push_agent, on_handoff=_note_handoff("push")),
    triage_agent,
]
push_agent.handoffs = [
    handoff(whatsapp_agent, on_handoff=_note_handoff("whatsapp")),
    triage_agent,
]

AGENTS_BY_NAME = {
    triage_agent.name: triage_agent,
    whatsapp_agent.name: whatsapp_agent,
    push_agent.name: push_agent,
}

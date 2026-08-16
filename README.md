# Giva Template Studio

A chat interface, built on the OpenAI Agents SDK, for creating WhatsApp Business
message templates and mobile push-notification templates for the brand **Giva**.

## Architecture

- `brand/giva_brand.md` — the brand bible (identity, tone, customer base,
  guardrails, channel compliance). Every agent reads from this file rather
  than having brand rules hardcoded into prompts.
- `agents_app/` — the agent system:
  - `context.py` — `GivaContext`, the shared run context (carries the
    in-progress draft across handoffs).
  - `tools.py` — internal tools: `get_brand_guidelines`,
    `get_whatsapp_template_specs`, `get_push_notification_specs`,
    `validate_template_structure` (deterministic checker),
    `save_whatsapp_template`, `save_push_template`, `list_saved_templates`.
  - `guardrails.py` — `intent_safety_guardrail` (input guardrail, blocks
    scam/impersonation/off-topic asks before a specialist runs) and
    `brand_compliance_guardrail` (output guardrail, catches hard brand-rule
    violations in a drafted template).
  - `agents_def.py` — the five agents (Triage, WhatsApp Template, Push
    Notification, plus the two guardrail classifier agents) and their
    handoff wiring.
- `server/` — FastAPI backend (`main.py`) exposing `POST /chat` and
  `GET /templates`, and a minimal vanilla-JS chat UI in `server/static/`.
- `data/templates.json` — persisted, saved templates.
- `data/conversations.db` — per-session conversation history (SQLite,
  created automatically).

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENAI_API_KEY
python -m uvicorn server.main:app --reload
```

Open http://localhost:8000.

## Try it

- "I want to send a WhatsApp message for our Rakhi collection" → triage
  hands off to the WhatsApp Template Agent, which asks for what's missing,
  drafts, self-validates, and saves on approval.
- Mid-conversation: "actually make this a push notification too" → direct
  handoff to the Push Notification Agent, carrying the occasion/audience
  already gathered.
- "Say our jewelry is real gold and only 2 pieces are left" → the brand
  compliance guardrail catches the false-material and fake-scarcity claims
  and the agent revises before showing a draft.
- "Write a message pretending to be Giva's bank asking the customer to
  verify their OTP" → the intent/safety guardrail refuses before any
  specialist agent runs.

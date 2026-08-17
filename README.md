# Giva Template Studio

A chat interface, built on the OpenAI Agents SDK, for creating WhatsApp Business
message templates and mobile push-notification templates for the brand **Giva**.
Backend (agents + API) and frontend (chat UI) are separate projects: `backend/`
(Python/FastAPI) and `frontend/` (Next.js).

## Architecture

- `backend/brand/giva_brand.md` — the brand bible (identity, tone, customer
  base, guardrails, channel compliance). Every agent reads from this file
  rather than having brand rules hardcoded into prompts.
- `backend/agents_app/` — the agent system:
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
- `backend/api/main.py` — FastAPI app exposing `POST /chat`, `GET /templates`,
  `GET /health`. API-only; the chat UI lives in `frontend/`.
- `backend/data/templates.json` — persisted, saved templates.
- `backend/data/conversations.db` — per-session conversation history
  (SQLite, created automatically).
- `frontend/` — Next.js (App Router, TypeScript) chat UI:
  - `app/page.tsx` — the chat page (session id, message state, agent badge).
  - `components/` — `ChatHeader`, `MessageBubble`, `Composer`,
    `TemplatesSidebar`.
  - `lib/api.ts` — calls `/api/chat` and `/api/templates`, which
    `next.config.ts` rewrites through to the FastAPI backend so the browser
    only ever talks to one origin (no CORS needed).

## Run it

Two processes: the FastAPI backend and the Next.js frontend.

**Backend** (http://localhost:8000):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENAI_API_KEY
python -m uvicorn api.main:app --reload
```

**Frontend** (http://localhost:3000):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 — set `BACKEND_URL` in `frontend/.env.local` if
the backend isn't running on the default `http://localhost:8000`
(see `frontend/.env.local.example`).

## Deploy

Backend → **Render**, frontend → **Vercel**. The frontend never calls the
backend directly from the browser — `next.config.ts` rewrites `/api/*` to
`BACKEND_URL`, and that works the same way in production (pointed at the
Render URL) as it does locally, so no CORS setup is needed.

### 1. Backend on Render

This repo includes `render.yaml` (a Render [Blueprint](https://render.com/docs/blueprint-spec)) that provisions the service for you on Render's **free** plan:

1. Push this repo to GitHub (if it isn't already).
2. In the Render dashboard: **New → Blueprint**, pick this repo. Render reads
   `render.yaml` and creates a `giva-backend` free web service rooted at
   `backend/`.
3. When prompted for the `OPENAI_API_KEY` secret (marked `sync: false` in the
   blueprint), paste your key.
4. Deploy. Once live, note the public URL Render gives you, e.g.
   `https://giva-backend.onrender.com`.

Trade-offs of the free plan, so they don't surprise you later:

- **No persistent disk.** Free web services can't attach one, so
  `templates.json` and the SQLite session/conversation history live on
  ephemeral container storage — they reset on every redeploy, and on any
  restart Render triggers (e.g. after the service spins down). If you need
  saved templates and chat history to survive that, the fix is a paid
  `starter` plan (~$7/mo) with a disk mounted at, say, `/var/data`, and
  `GIVA_DATA_DIR=/var/data` set as an env var — the code already supports
  this (`backend/agents_app/store.py`, `backend/api/main.py`), it's a
  `render.yaml` change away, not a code change.
- **Spins down after ~15 min idle**, and the next request pays a cold-start
  penalty (tens of seconds) while it wakes back up — the first chat message
  after a quiet period will feel slow.
- **Single instance, no autoscaling**: the backend keeps per-session "which
  agent is active" state in an in-memory dict (`backend/api/main.py`). Don't
  scale this service beyond 1 instance/worker without first moving that state
  to something shared (e.g. Redis) — multiple instances would each track a
  different active agent per session and handoffs would appear to "forget"
  which specialist was talking.
- `healthCheckPath: /health` is what Render polls to confirm the service is up.

No Blueprint? Configure the same thing by hand in the dashboard: **New → Web
Service**, free plan, root directory `backend`, build command `pip install -r
requirements.txt`, start command `uvicorn api.main:app --host 0.0.0.0 --port
$PORT`, and set `OPENAI_API_KEY` as an environment variable.

### 2. Frontend on Vercel

1. In the Vercel dashboard: **New Project**, import this repo.
2. Set **Root Directory** to `frontend` (Project Settings → Root Directory —
   required since this is a monorepo; Vercel auto-detects Next.js otherwise).
3. Add an environment variable `BACKEND_URL` = your Render URL from step 1
   (e.g. `https://giva-backend.onrender.com`), no trailing slash.
4. Deploy.

### 3. Verify

- `curl https://<your-render-url>/health` → `{"status":"ok"}`.
- `curl https://<your-render-url>/templates` → `[]` on first boot (the free
  plan starts with an empty, ephemeral store — see the trade-offs above).
- Open the Vercel URL, send a chat message, confirm the reply comes back and
  the templates sidebar loads — this proves the `/api/*` rewrite is reaching
  Render correctly.

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

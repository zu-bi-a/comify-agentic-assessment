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
  - `db.py` — the Postgres engine/schema shared by everything below
    (`threads`, `chat_messages`, `templates` tables, plus the Agents SDK's
    own `agent_sessions`/`agent_messages` tables it bootstraps).
  - `store.py` — saved-template CRUD (Postgres-backed).
  - `threads.py` — chat thread + message CRUD (Postgres-backed).
- `backend/api/main.py` — FastAPI app exposing `POST /chat`,
  `GET/PATCH/DELETE /threads`, `GET /threads/{id}/messages`,
  `GET /templates`, `GET /health`. API-only; the chat UI lives in
  `frontend/`.
- **Postgres** is the single source of truth for everything that needs to
  survive a restart: chat threads, their display transcript
  (`chat_messages`), the Agents SDK's own raw turn history it needs to keep
  the model's context (`agent_sessions`/`agent_messages`, via
  `agents.extensions.memory.SQLAlchemySession`), and saved templates. Nothing
  is written to disk on the backend process anymore.
- `docker-compose.yml` (repo root) — a local Postgres for development, on
  host port `5433` so it doesn't collide with a Postgres you may already
  have running. `docker compose up -d` before starting the backend locally.
- `frontend/` — Next.js (App Router, TypeScript) chat UI:
  - `app/page.tsx` — the chat page: active thread, message state, agent
    badge, sidebar tab.
  - `components/` — `ChatHeader`, `MessageBubble`, `Composer`, `Sidebar`
    (the Chats / Saved templates toggle), `ChatsPanel` (thread list — new
    chat, switch, rename, delete), `TemplatesPanel` (formerly
    `TemplatesSidebar`).
  - `lib/api.ts` — calls `/api/chat`, `/api/threads*`, `/api/templates`,
    which `next.config.ts` rewrites through to the FastAPI backend so the
    browser only ever talks to one origin (no CORS needed).

## Run it

Two processes: the FastAPI backend and the Next.js frontend.

**Postgres** (once, from the repo root):

```bash
docker compose up -d db   # local Postgres on localhost:5433
```

**Backend** (http://localhost:8000):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENAI_API_KEY (DATABASE_URL default matches docker-compose)
python -m uvicorn api.main:app --reload
```

Tables (`threads`, `chat_messages`, `templates`, and the Agents SDK's own
session tables) are created automatically on startup — no separate migration
step for this lightweight setup.

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

This repo includes `render.yaml` (a Render [Blueprint](https://render.com/docs/blueprint-spec)) that provisions both the web service and a Postgres database for you on Render's **free** plan:

1. Push this repo to GitHub (if it isn't already).
2. In the Render dashboard: **New → Blueprint**, pick this repo. Render reads
   `render.yaml` and creates a `giva-backend` free web service rooted at
   `backend/`, plus a free `giva-db` Postgres instance whose connection
   string is wired into the service as `DATABASE_URL` automatically
   (`fromDatabase` in the blueprint).
3. When prompted for the `OPENAI_API_KEY` secret (marked `sync: false` in the
   blueprint), paste your key.
4. Deploy. Once live, note the public URL Render gives you, e.g.
   `https://giva-backend.onrender.com`.

Trade-offs of the free plan, so they don't surprise you later:

- **Chat threads, messages, and saved templates now live in Postgres**, not
  on the web service's own disk — so they survive redeploys and restarts.
  The one caveat is Render's **free Postgres plan expires 30 days after
  creation** (Render's limit, not this app's); upgrade it to a paid plan
  before then if you want the data to persist longer.
- **Spins down after ~15 min idle**, and the next request pays a cold-start
  penalty (tens of seconds) while it wakes back up — the first chat message
  after a quiet period will feel slow.
- **Single instance, no autoscaling**: the backend keeps per-thread "which
  agent is active" state in an in-memory dict as a cache (`backend/api/main.py`)
  over what's really persisted in Postgres. Don't scale this service beyond
  1 instance/worker without first moving that cache to something shared
  (e.g. Redis) — multiple instances would each track a different active
  agent per thread in memory and handoffs would appear to "forget" which
  specialist was talking mid-conversation (though the next message would
  still resolve correctly from Postgres).
- `healthCheckPath: /health` is what Render polls to confirm the service is up.

No Blueprint? Configure the same thing by hand in the dashboard: **New →
PostgreSQL** (free plan) to create the database, then **New → Web Service**,
free plan, root directory `backend`, build command `pip install -r
requirements.txt`, start command `uvicorn api.main:app --host 0.0.0.0 --port
$PORT`, and set `OPENAI_API_KEY` and `DATABASE_URL` (the database's
"Internal Connection String") as environment variables.

### 2. Frontend on Vercel

1. In the Vercel dashboard: **New Project**, import this repo.
2. Set **Root Directory** to `frontend` (Project Settings → Root Directory —
   required since this is a monorepo; Vercel auto-detects Next.js otherwise).
3. Add an environment variable `BACKEND_URL` = your Render URL from step 1
   (e.g. `https://giva-backend.onrender.com`), no trailing slash.
4. Deploy.

### 3. Verify

- `curl https://<your-render-url>/health` → `{"status":"ok"}`.
- `curl https://<your-render-url>/templates` → `[]` on first boot (a fresh
  Postgres database, empty until someone saves a template).
- Open the Vercel URL, send a chat message, confirm the reply comes back and
  a new entry appears under the Chats tab in the sidebar — this proves the
  `/api/*` rewrite is reaching Render correctly.

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

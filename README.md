# Workout Agent

An AI-powered endurance coaching system that connects to your Strava account, analyses your training data, generates personalised multi-week plans, and lets you chat with a coaching agent in real time. Plans adapt intelligently — only when your latest activity shows meaningful deviation from what was expected.

---

## Table of Contents

- [How it works](#how-it-works)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Quick start](#quick-start)
- [Web UI](#web-ui)
- [CLI commands](#cli-commands)
- [API reference](#api-reference)
- [Strava webhook](#strava-webhook)
- [Codebase structure](#codebase-structure)
- [Adding a new skill](#adding-a-new-skill)
- [LLM providers](#llm-providers)

---

## How it works

```
Strava API
    │
    ▼
WorkoutAgent  ──────────────────────────────────────────────────────────
  │  LangGraph StateGraph                                               │
  │                                                                     │
  ├─ fetch_activities  → pulls recent Strava sessions                   │
  ├─ analyze_fitness   → LLM fitness summary (load, trends, readiness)  │
  │                                                                     │
  ├─[mode=plan]  create_plan  → full multi-week Markdown plan           │
  └─[mode=adapt] adapt_plan   → structured LLM decision:               │
                                  needs_adaptation? yes/no             │
                                  if yes → rewrites remaining weeks     │
                                  if no  → returns reason, plan untouched
                                                                        │
CoachChat  ──────────────────────────────────────────────────────────────
  │  LangGraph ReAct agent with 10 skill-tools
  │
  ├─ reads Strava live (get_recent_activities, get_latest_activity, …)
  ├─ reads / writes the plan file (get_current_plan, save_plan)
  └─ calculates zones, paces, race estimates
```

Every plan is stored as a JSON file (`plans/workout_plan.json`) and persisted in a named Docker volume so it survives container restarts.

When the web Adapt button is pressed (or a Strava webhook fires), the system:
1. Fetches the latest activity and compares its ID against `last_activity_id` stored in the plan → **no new activity? returns immediately** with an info message.
2. If there is a new activity, runs the agent and asks the LLM to decide whether the performance deviates meaningfully from the plan.
3. **No deviation?** Saves the activity ID (so the next press won't re-analyse it) and returns the LLM's plain-language assessment.
4. **Deviation detected?** Saves the updated plan as a *pending* draft. You review the diff, then accept or reject it.

---

## Architecture

```
workout-agent/
├── app/                   Python backend
│   ├── agent.py           LangGraph planning & adaptation graph
│   ├── api.py             FastAPI — REST, SSE, WebSocket, Strava webhook
│   ├── chat.py            CLI interactive chat (CoachChat class)
│   ├── config.py          LLM factory + PLAN_FILE path
│   ├── skills.py          10 @tool functions available to the ReAct agent
│   ├── strava.py          StravaClient (OAuth token refresh + data fetch)
│   └── tools.py           AthleteState pydantic model (LangGraph state)
│
├── web/                   React frontend
│   └── src/
│       ├── App.tsx         Root layout: plan panel + chat sidebar
│       ├── types.ts        Shared TypeScript interfaces
│       ├── components/
│       │   ├── Header.tsx          Top bar: title, last-updated, Adapt button
│       │   ├── PendingBanner.tsx   Amber review bar: diff / accept / reject
│       │   ├── plan/
│       │   │   ├── PlanView.tsx    7-column calendar grid with click-to-expand cards
│       │   │   └── PlanDiff.tsx    Git-style line diff (current vs pending)
│       │   └── chat/
│       │       └── Chat.tsx        Streaming chat UI with tool activity indicator
│       ├── hooks/
│       │   ├── usePlan.ts   Plan state + SSE subscription + adapt/accept/reject
│       │   └── useChat.ts   WebSocket connection + token streaming
│       └── lib/
│           ├── api.ts         Typed fetch wrapper for all REST calls
│           └── planParser.ts  Markdown → ParsedWeek[] (days, types, titles)
│
├── docker/
│   ├── Dockerfile         CLI image (uv + Python, entrypoint: main.py)
│   └── Dockerfile.api     Multi-stage: Node 20 builds web/dist → Python backend serves it
│
├── scripts/
│   └── register_webhook.py   One-time Strava webhook registration
│
├── docker-compose.yml     Two services: app (cli), api (port 8000)
├── justfile               Task runner — all common commands
├── main.py                CLI entry point: plan / adapt / chat
└── pyproject.toml         Python dependencies (uv)
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker + Compose | v2+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| `just` | any | `curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh \| bash -s -- --to ~/.local/bin` |
| `uv` | any | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 20+ | Only needed for local frontend dev |

---

## Configuration

Copy `.env.example` to `.env` (or create `.env`) and fill in your credentials:

```ini
# ── Strava ─────────────────────────────────────────────────────────────────────
# Create an app at https://www.strava.com/settings/api
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REFRESH_TOKEN=      # obtained via the OAuth flow
STRAVA_VERIFY_TOKEN=       # any random string — used to validate webhook subscription

# ── Groq (default LLM, free at console.groq.com) ───────────────────────────────
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile   # optional override

# ── OpenAI (optional — set LLM_PROVIDER=openai to use) ─────────────────────────
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini             # optional override

# ── LLM provider selection ──────────────────────────────────────────────────────
# LLM_PROVIDER=openai                # uncomment to switch; default is groq
```

> **Never commit `.env` to git.** It is already in `.gitignore`.

### How to get a Strava refresh token

1. Go to [strava.com/settings/api](https://www.strava.com/settings/api) and create an application.
2. Set the Authorization Callback Domain to `localhost`.
3. Visit this URL in your browser (replace `CLIENT_ID`):
   ```
   https://www.strava.com/oauth/authorize?client_id=CLIENT_ID&redirect_uri=http://localhost&response_type=code&scope=activity:read_all
   ```
4. Authorise the app — you'll be redirected to `http://localhost/?code=XXXX`.
5. Exchange the code for tokens:
   ```bash
   curl -X POST https://www.strava.com/oauth/token \
     -d client_id=CLIENT_ID \
     -d client_secret=CLIENT_SECRET \
     -d code=XXXX \
     -d grant_type=authorization_code
   ```
6. Copy the `refresh_token` from the response into `.env`.

---

## Quick start

```bash
# 1. Clone and configure
git clone <repo>
cd workout-agent
cp .env.example .env   # then fill in your keys

# 2. Build everything
just build

# 3. Start the API (serves the web UI at http://localhost:8000)
just up

# 4. Create your first plan
just plan objective="Run a sub-50 minute 10K in 8 weeks"
```

The web UI is now live at **http://localhost:8000**.

---

## Web UI

The interface is split into two panels:

### Left — Plan panel

Displays your training plan as a **7-column weekly calendar**. Each day card shows the workout type (colour-coded), title, and a compact preview. Click a card to expand the full session details in Markdown.

Week navigation tabs at the top let you flick between weeks. The current week index resets to Week 1 whenever a new plan is loaded.

**Workout type colours**

| Type | Colour |
|------|--------|
| Run | Blue |
| Bike | Orange |
| Swim | Cyan |
| Strength | Purple |
| Rest / Recovery | Grey |
| Other | Green |

#### Adapt button

Pressing **Adapt** in the header triggers the smart adaptation flow:

- **No new activity** — a blue info bar appears: *"No new activities since last check — your plan is up to date."*
- **New activity, no deviation** — a blue info bar shows the LLM's assessment, e.g. *"Your tempo run was on target. No changes needed."*
- **New activity, deviation detected** — an amber banner appears. You can:
  - **View diff** — switch to a git-style line-by-line diff of current vs proposed plan
  - **Accept** — promotes the pending plan to current
  - **Discard** — throws away the proposed changes

### Right — Chat panel

A dark-themed streaming chat with your AI coach. The coach has access to all your Strava data and your current plan. Example questions:

- *"How did my training volume look this week?"*
- *"What are my heart rate zones if my max HR is 185?"*
- *"What pace do I need to run a sub-2h half marathon?"*
- *"Update my plan to add a rest day on Wednesday."*

Any plan the coach produces or modifies is automatically saved to disk via the `save_plan` tool.

---

## CLI commands

All commands run inside Docker containers. You don't need a local Python environment.

```bash
# Create a new training plan
just plan objective="Complete an Ironman 70.3 in 20 weeks"

# Adapt the plan after your latest Strava activity
just adapt

# Start an interactive coaching chat in the terminal
just chat

# Start the API server (web UI)
just up

# Follow live logs
just logs

# Rebuild all images (after code changes)
just build

# Full teardown (keeps plan data)
just down

# Full teardown and wipe all data
just down-clean
```

---

## API reference

Base URL: `http://localhost:8000`

### REST

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/plan` | Return current plan JSON |
| `POST` | `/api/plan/adapt` | Run smart adaptation; returns `{ status, message?, pending_plan? }` |
| `POST` | `/api/plan/accept` | Promote pending plan to current |
| `POST` | `/api/plan/reject` | Discard pending plan |

#### `POST /api/plan/adapt` response

```jsonc
// No new activity since last check
{ "status": "no_new_activity", "message": "No new activities since last check — your plan is up to date." }

// New activity, performance in line with plan
{ "status": "no_changes", "message": "<LLM assessment>" }

// New activity, plan updated — pending review
{ "status": "adapted", "pending_plan": "<full Markdown plan>" }
```

### SSE — real-time events

`GET /api/events` — text/event-stream

Each `data:` line is a JSON object:

| `type` | Meaning |
|--------|---------|
| `plan_adapted` | Auto-adapt (webhook) produced a pending plan |
| `plan_accepted` | Pending plan was accepted |
| `plan_updated` | Plan was saved by the chat agent |

### WebSocket

`WS /api/ws/chat` — streaming coaching chat

**Send:**
```json
{ "message": "How did I do this week?" }
```

**Receive (sequence of frames):**
```json
{ "type": "tool_start", "name": "get_weekly_volume" }
{ "type": "tool_end",   "name": "get_weekly_volume" }
{ "type": "token",      "content": "This " }
{ "type": "token",      "content": "week you..." }
{ "type": "done",       "tools_used": ["get_weekly_volume"] }
```

---

## Strava webhook

The webhook allows Strava to push a notification whenever you record a new activity. The API will automatically run the smart adaptation and, if the plan needs changing, create a pending draft visible in the web UI.

### Setup (one time)

1. Start the API and expose it publicly (ngrok is the easiest option for local dev):
   ```bash
   just up
   just ngrok          # opens https://<id>.ngrok-free.app → localhost:8000
   ```

2. Register the webhook with Strava:
   ```bash
   just register-webhook url=https://<id>.ngrok-free.app
   ```

3. Verify registration:
   ```bash
   just list-webhooks
   ```

The webhook endpoint validates using `STRAVA_VERIFY_TOKEN` from `.env`.

To remove a webhook:
```bash
just delete-webhook id=<subscription_id>
```

---

## Codebase structure

### `app/agent.py` — LangGraph planning graph

Builds a `StateGraph` with five nodes:

```
START → fetch_activities → analyze_fitness → [route by mode]
                                                ├─ plan  → create_plan  → generate_response → END
                                                └─ adapt → adapt_plan   → generate_response → END
```

**`adapt_plan`** uses `with_structured_output(AdaptDecision)` to force the LLM to return a typed response:
```python
class AdaptDecision(BaseModel):
    needs_adaptation: bool
    reason: str           # 2–4 sentence assessment
    updated_plan: str | None   # full plan if needs_adaptation else None
```

This means the plan is only rewritten when the LLM explicitly decides it should be.

### `app/api.py` — FastAPI application

- **SSE broadcast** — `_sse_queues: list[asyncio.Queue]`. Each connected client gets its own queue; `_broadcast()` fans out to all.
- **Pending plan flow** — `adapt` saves to `pending_plan` key in the JSON file; `accept` moves it to `plan`; `reject` removes it. The `last_activity_id` field prevents re-analysing the same activity.
- **WebSocket chat** — runs `create_react_agent` and streams events via `astream_events(..., version="v2")`. History is held per-connection in memory and seeded with the current plan on connect.

### `app/skills.py` — agent tools

10 `@tool` functions, all registered in `ALL_SKILLS`:

| Tool | What it does |
|------|-------------|
| `get_recent_activities` | Last N Strava activities (compact stats) |
| `get_latest_activity` | Single most recent activity (full stats) |
| `get_weekly_volume` | Per-sport volume aggregated by week |
| `get_current_plan` | Read plan from disk |
| `get_plan_objective` | Read just the objective |
| `save_plan` | Write updated plan to disk |
| `calculate_heart_rate_zones` | 5-zone HR model from max HR |
| `calculate_power_zones` | 7-zone Coggan power model from FTP |
| `estimate_race_time` | Finish time from distance + pace |
| `calculate_required_pace` | Required pace from distance + target time |

All numeric parameters are typed `int | str` or `float | str` (with manual coercion inside) to handle Groq's tendency to pass numbers as strings in tool calls.

### `app/strava.py` — Strava API client

`StravaClient` handles OAuth token refresh automatically on every request (Strava access tokens expire after 6 hours). A lazy module-level singleton is returned by `get_client()`.

### `web/src/lib/planParser.ts` — Markdown plan parser

`parsePlan(markdown)` turns the free-form Markdown plan the LLM produces into a structured `ParsedWeek[]`:
- Splits on `## Week N` headings (falls back to treating the whole plan as one week)
- Within each week, splits on `### Monday` / `**Tuesday**` style headings
- Infers workout type from keywords (`run`, `tempo`, `bike`, `ftp`, `swim`, `strength`, `rest`, …)

### `web/src/hooks/usePlan.ts` — plan state hook

Manages: plan data, pending notifications, the adapt/accept/reject mutations, and the SSE subscription. Uses `useRef` for the notification value read inside `refresh()` to avoid a stale-closure that would cause the SSE `EventSource` to reconnect on every notification change.

### `web/src/hooks/useChat.ts` — WebSocket chat hook

Maintains a persistent WebSocket with 2-second auto-reconnect. Streams tokens into the last assistant message in-place using append-in-state rather than replacing the array.

---

## Adding a new skill

1. Add a new `@tool` function to `app/skills.py`:
   ```python
   @tool
   def my_new_skill(param: str) -> str:
       """Describe what this skill does — the LLM reads this docstring."""
       ...
       return "result as string"
   ```

2. Add it to `ALL_SKILLS` at the bottom of the file:
   ```python
   ALL_SKILLS = [
       ...
       my_new_skill,
   ]
   ```

The agent will discover and use it automatically in both the web chat and CLI chat.

---

## LLM providers

The default provider is **Groq** (free tier, fast). Switch to OpenAI by setting `LLM_PROVIDER=openai` in `.env`.

| Provider | Env var | Default model | Notes |
|----------|---------|---------------|-------|
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | Free tier, ~300 req/day |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` | Paid, change via `OPENAI_MODEL` |

To use a different Groq model (e.g. `mixtral-8x7b-32768`), set `GROQ_MODEL` in `.env`.


```bash
python main.py
```

### Files

- `main.py` — entry point that builds a LangGraph agent with tools and runs it.
- `tools.py` — defines `search`, `scrape`, and `save_to_text` tools used by the agent.
- `pyproject.toml` — project dependencies.

### Notes

- The agent is created using `langgraph.prebuilt.create_react_agent`.
- The tool names are now aligned with the prompt: `scrape`, `search`, and `save_to_text`.
- Structured output is validated using Pydantic.

"""
FastAPI application — REST API, streaming WebSocket chat, SSE events, and Strava webhook.

Endpoints:
  GET  /api/plan               → current plan JSON
  POST /api/plan/adapt         → trigger manual adaptation (saves as pending)
  POST /api/plan/accept        → promote pending plan to current
  POST /api/plan/reject        → discard pending plan
  GET  /api/events             → SSE stream for real-time notifications
  WS   /api/ws/chat            → streaming coaching chat
  GET  /webhook                → Strava subscription validation
  POST /webhook                → Strava activity event (auto-adapt → pending)

The built React frontend is served from web/dist/ at /.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app.agent import WorkoutAgent
from app.config import PLAN_FILE, build_llm
from app.skills import ALL_SKILLS
from app.strava import get_client as strava_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Workout Agent API")

# Allow Vite dev server during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Plan helpers ───────────────────────────────────────────────────────────────

def _load_plan() -> dict:
    if not PLAN_FILE.exists():
        return {}
    return json.loads(PLAN_FILE.read_text())


def _save_plan(data: dict) -> None:
    PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLAN_FILE.write_text(json.dumps(data, indent=2))


# ── SSE event bus ──────────────────────────────────────────────────────────────

_sse_queues: list[asyncio.Queue] = []


async def _broadcast(event: dict) -> None:
    for q in _sse_queues:
        await q.put(event)


# ── Plan API ───────────────────────────────────────────────────────────────────

@app.get("/api/plan")
def get_plan():
    data = _load_plan()
    if not data:
        raise HTTPException(status_code=404, detail="No plan found")
    return data


@app.post("/api/plan/adapt")
async def trigger_adapt():
    data = _load_plan()
    if not data:
        raise HTTPException(status_code=404, detail="No existing plan. Create one first.")

    # ── Check for a new activity since last adaptation ─────────────────────
    latest = strava_client().get_latest_activity()
    latest_id = latest.get("id") if latest else None

    if not latest or latest_id == data.get("last_activity_id"):
        return {
            "status": "no_new_activity",
            "message": "No new activities since last check — your plan is up to date.",
        }

    # ── Run smart adaptation (LLM decides if plan needs to change) ─────────
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: WorkoutAgent(build_llm(), strava_client()).run(
            objective=data["objective"],
            mode="adapt",
            current_plan=data["plan"],
            latest_activity=latest,
        ),
    )

    # Always record the activity we just evaluated
    data["last_activity_id"] = latest_id

    if not result.get("updated_plan"):
        _save_plan(data)
        return {
            "status": "no_changes",
            "message": result.get("adapt_reason") or "Performance as expected — no plan changes needed.",
        }

    data["last_activity_id"] = latest_id
    data["pending_plan"] = result["updated_plan"]
    data["pending_updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_plan(data)
    await _broadcast({"type": "plan_adapted", "message": "Plan adapted — review and accept changes."})
    return {"status": "adapted", "pending_plan": result["updated_plan"]}


@app.post("/api/plan/accept")
async def accept_plan():
    data = _load_plan()
    if not data.get("pending_plan"):
        raise HTTPException(status_code=404, detail="No pending plan to accept")
    data["plan"] = data.pop("pending_plan")
    data["updated_at"] = data.pop("pending_updated_at", datetime.now(timezone.utc).isoformat())
    _save_plan(data)
    await _broadcast({"type": "plan_accepted"})
    return data


@app.post("/api/plan/reject")
async def reject_plan():
    data = _load_plan()
    data.pop("pending_plan", None)
    data.pop("pending_updated_at", None)
    _save_plan(data)
    return {"status": "ok"}


# ── SSE ────────────────────────────────────────────────────────────────────────

@app.get("/api/events")
async def sse_events(request: Request):
    queue: asyncio.Queue = asyncio.Queue()
    _sse_queues.append(queue)

    async def generate() -> AsyncIterator[str]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if queue in _sse_queues:
                _sse_queues.remove(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── WebSocket chat ─────────────────────────────────────────────────────────────

_CHAT_SYSTEM_PROMPT = """\
You are an expert endurance coach and training assistant.
You have access to tools that fetch real Strava activities, read the athlete's training plan,
calculate training zones, estimate race times, and more.

Use tools proactively when questions involve data (e.g. "how did I do this week?" → call get_weekly_volume).
Be concise, specific, and encouraging. Always base advice on actual data when available.

IMPORTANT: Whenever you produce or modify a training plan, always call save_plan to persist it.\
"""


@app.websocket("/api/ws/chat")
async def chat_ws(websocket: WebSocket):
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.prebuilt import create_react_agent

    await websocket.accept()

    plan_data = _load_plan()
    history = []
    if plan_data.get("plan"):
        history = [
            HumanMessage(content="Here is my current training plan — keep it in mind for our conversation."),
            AIMessage(content=(
                f"Got it. Your current plan:\n\n"
                f"**Objective:** {plan_data.get('objective', '')}\n"
                f"**Last updated:** {plan_data.get('updated_at', '')}\n\n"
                f"{plan_data['plan']}"
            )),
        ]

    agent = create_react_agent(build_llm(), ALL_SKILLS, prompt=_CHAT_SYSTEM_PROMPT)
    last_updated_at = plan_data.get("updated_at")

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()
            if not message:
                continue

            history.append(HumanMessage(content=message))
            full_response = ""
            current_tools: list[str] = []

            async for event in agent.astream_events({"messages": history}, version="v2"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        full_response += chunk
                        await websocket.send_json({"type": "token", "content": chunk})
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    current_tools.append(tool_name)
                    await websocket.send_json({"type": "tool_start", "name": tool_name})
                elif kind == "on_tool_end":
                    await websocket.send_json({"type": "tool_end", "name": event.get("name", "")})

            await websocket.send_json({"type": "done", "tools_used": list(set(current_tools))})
            history.append(AIMessage(content=full_response))

            # Notify frontend if plan was saved during this turn
            new_updated_at = _load_plan().get("updated_at")
            if new_updated_at != last_updated_at:
                last_updated_at = new_updated_at
                await _broadcast({"type": "plan_updated"})

    except WebSocketDisconnect:
        pass


# ── Strava webhook ─────────────────────────────────────────────────────────────

_VERIFY_TOKEN = os.environ.get("STRAVA_VERIFY_TOKEN", "")


@app.get("/webhook")
def validate_subscription(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Unexpected hub.mode")
    if not _VERIFY_TOKEN or hub_verify_token != _VERIFY_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid verify_token")
    log.info("Strava webhook subscription validated.")
    return JSONResponse({"hub.challenge": hub_challenge})


@app.post("/webhook")
async def receive_event(request: Request):
    payload = await request.json()
    log.info("Strava event: %s", payload)
    if payload.get("object_type") == "activity" and payload.get("aspect_type") == "create":
        data = _load_plan()
        if not data:
            return {"status": "no_plan"}
        log.info("New activity → queuing auto-adapt (will save as pending for review)")
        asyncio.create_task(_auto_adapt(data))
    return {"status": "ok"}


async def _auto_adapt(plan_data: dict) -> None:
    loop = asyncio.get_event_loop()
    try:
        # Fetch latest activity once to pass into the agent (avoids double fetch)
        latest = strava_client().get_latest_activity()
        latest_id = latest.get("id") if latest else None

        result = await loop.run_in_executor(
            None,
            lambda: WorkoutAgent(build_llm(), strava_client()).run(
                objective=plan_data["objective"],
                mode="adapt",
                current_plan=plan_data["plan"],
                latest_activity=latest,
            ),
        )

        plan_data["last_activity_id"] = latest_id

        if not result.get("updated_plan"):
            _save_plan(plan_data)
            log.info("Auto-adapt: no plan changes needed — %s", result.get("adapt_reason", ""))
            return

        plan_data["pending_plan"] = result["updated_plan"]
        plan_data["pending_updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_plan(plan_data)
        await _broadcast({
            "type": "plan_adapted",
            "message": "New Strava activity detected — plan adapted. Review and accept changes.",
        })
        log.info("Auto-adapt complete. Awaiting user approval.")
    except Exception as exc:
        log.exception("Auto-adapt failed: %s", exc)


# ── Serve built frontend ───────────────────────────────────────────────────────

_STATIC_DIR = Path(__file__).parent.parent / "web" / "dist"
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

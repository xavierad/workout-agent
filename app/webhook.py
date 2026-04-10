"""
Strava Webhook receiver.

Strava calls GET /webhook to validate the subscription (one-time setup).
Strava calls POST /webhook every time an activity is created/updated/deleted.

On activity creation we trigger `main.py adapt` so the plan is updated.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(title="Workout Agent – Strava Webhook")

VERIFY_TOKEN = os.environ.get("STRAVA_VERIFY_TOKEN", "")
PLAN_FILE = Path("plans/workout_plan.json")

@app.get("/webhook")
def validate_subscription(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    """Strava sends this once when you register the webhook subscription."""
    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Unexpected hub.mode")
    if not VERIFY_TOKEN or hub_verify_token != VERIFY_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid verify_token")
    log.info("Webhook subscription validated.")
    return JSONResponse({"hub.challenge": hub_challenge})


# ── Event receiver (POST) ──────────────────────────────────────────────────────

@app.post("/webhook")
async def receive_event(request: Request):
    """
    Strava sends an event payload like:
    {
      "aspect_type": "create",
      "event_time": 1549560669,
      "object_id": 1234567890,   ← activity id
      "object_type": "activity",
      "owner_id": 1234567890,
      "subscription_id": 12345
    }
    """
    payload = await request.json()
    log.info("Received Strava event: %s", payload)

    # Only react to new activities
    if payload.get("object_type") == "activity" and payload.get("aspect_type") == "create":
        if not PLAN_FILE.exists():
            log.warning("No workout plan found – skipping adapt. Run `plan` first.")
            return {"status": "no_plan"}

        log.info("New activity detected – triggering plan adaptation asynchronously.")
        asyncio.create_task(_run_adapt())

    return {"status": "ok"}


async def _run_adapt():
    """Run adapt in-process without blocking the webhook response."""
    import json as _json
    from app.config import PLAN_FILE as _PLAN_FILE
    from app.agent import graph as _graph

    loop = asyncio.get_event_loop()
    try:
        def _adapt():
            if not _PLAN_FILE.exists():
                return
            data = _json.loads(_PLAN_FILE.read_text())
            result = _graph.invoke({
                "objective": data["objective"],
                "mode": "adapt",
                "current_plan": data["plan"],
            })
            _PLAN_FILE.write_text(_json.dumps({
                "objective": data["objective"],
                "plan": result["updated_plan"],
                "updated_at": __import__("datetime").datetime.utcnow().isoformat(),
            }, indent=2))
            log.info("Plan adapted.\n%s", result.get("coach_response", ""))

        await loop.run_in_executor(None, _adapt)
    except Exception as exc:
        log.exception("Unexpected error during plan adaptation: %s", exc)

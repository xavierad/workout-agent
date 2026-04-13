"""
Integration tests for the FastAPI application.

Uses httpx.AsyncClient against the real app with:
  - a temporary plan file (no disk side-effects)
  - mocked Strava (no real API calls)
  - mocked WorkoutAgent (no real LLM calls)
"""

import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import (
    EXTRACTED_ACTIVITY,
    PLAN_JSON,
    PLAN_JSON_WITH_PENDING,
    PLAN_MD_WEEKLY,
)


# ── App fixture ───────────────────────────────────────────────────────────────

@pytest.fixture
def app_with_plan(plan_file_with_data):
    """Return the FastAPI app with PLAN_FILE pointing to the temp file."""
    from app.api import app
    return app


@pytest.fixture
def app_no_plan(tmp_plan_file):
    """Return the FastAPI app with an empty (non-existent) plan file."""
    from app.api import app
    return app


@pytest.fixture
def app_with_pending(plan_file_with_pending):
    from app.api import app
    return app


@pytest_asyncio.fixture
async def client(app_with_plan):
    async with AsyncClient(transport=ASGITransport(app=app_with_plan), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def client_no_plan(app_no_plan):
    async with AsyncClient(transport=ASGITransport(app=app_no_plan), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def client_pending(app_with_pending):
    async with AsyncClient(transport=ASGITransport(app=app_with_pending), base_url="http://test") as c:
        yield c


# ── GET /api/plan ─────────────────────────────────────────────────────────────

class TestGetPlan:
    async def test_returns_plan_when_exists(self, client):
        resp = await client.get("/api/plan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["objective"] == PLAN_JSON["objective"]
        assert "plan" in data

    async def test_returns_404_when_no_plan(self, client_no_plan):
        resp = await client_no_plan.get("/api/plan")
        assert resp.status_code == 404

    async def test_response_includes_updated_at(self, client):
        resp = await client.get("/api/plan")
        assert "updated_at" in resp.json()


# ── POST /api/plan/accept ─────────────────────────────────────────────────────

class TestAcceptPlan:
    async def test_promotes_pending_to_current(self, client_pending, plan_file_with_pending):
        resp = await client_pending.post("/api/plan/accept")
        assert resp.status_code == 200
        data = json.loads(plan_file_with_pending.read_text())
        # pending_plan becomes plan
        assert "pending_plan" not in data
        assert "Monday" in data["plan"]

    async def test_returns_404_when_no_pending(self, client):
        resp = await client.post("/api/plan/accept")
        assert resp.status_code == 404

    async def test_accepted_plan_sets_updated_at(self, client_pending):
        resp = await client_pending.post("/api/plan/accept")
        assert "updated_at" in resp.json()


# ── POST /api/plan/reject ─────────────────────────────────────────────────────

class TestRejectPlan:
    async def test_removes_pending_plan(self, client_pending, plan_file_with_pending):
        resp = await client_pending.post("/api/plan/reject")
        assert resp.status_code == 200
        data = json.loads(plan_file_with_pending.read_text())
        assert "pending_plan" not in data

    async def test_preserves_current_plan(self, client_pending, plan_file_with_pending):
        await client_pending.post("/api/plan/reject")
        data = json.loads(plan_file_with_pending.read_text())
        assert data["plan"] == PLAN_JSON["plan"]

    async def test_returns_ok_status(self, client):
        resp = await client.post("/api/plan/reject")
        assert resp.json()["status"] == "ok"


# ── POST /api/plan/adapt ──────────────────────────────────────────────────────

class TestTriggerAdapt:
    async def test_returns_404_when_no_plan(self, client_no_plan):
        with patch("app.api.strava_client"):
            resp = await client_no_plan.post("/api/plan/adapt")
        assert resp.status_code == 404

    async def test_no_new_activity_returns_correct_status(self, client, plan_file_with_data):
        # Pre-set last_activity_id to match the mock's activity
        data = json.loads(plan_file_with_data.read_text())
        data["last_activity_id"] = EXTRACTED_ACTIVITY["id"]
        plan_file_with_data.write_text(json.dumps(data))

        mock_strava = MagicMock()
        mock_strava.get_latest_activity.return_value = EXTRACTED_ACTIVITY
        with patch("app.api.strava_client", return_value=mock_strava):
            resp = await client.post("/api/plan/adapt")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "no_new_activity"

    async def test_no_changes_when_llm_says_no_adaptation(self, client, plan_file_with_data):
        from app.agent import AdaptDecision
        decision = AdaptDecision(
            needs_adaptation=False,
            reason="Performance as expected.",
            updated_plan=None,
        )
        mock_strava = MagicMock()
        mock_strava.get_latest_activity.return_value = EXTRACTED_ACTIVITY

        mock_agent = MagicMock()
        mock_agent.run.return_value = {
            "updated_plan": None,
            "adapt_reason": "Performance as expected.",
        }

        with patch("app.api.strava_client", return_value=mock_strava), \
             patch("app.api.WorkoutAgent", return_value=mock_agent):
            resp = await client.post("/api/plan/adapt")

        body = resp.json()
        assert body["status"] == "no_changes"
        assert "expected" in body["message"]

    async def test_adapted_saves_pending_plan(self, client, plan_file_with_data):
        new_plan = "## Week 1\n\n### Monday\nExtra rest — fatigue detected\n"
        mock_strava = MagicMock()
        mock_strava.get_latest_activity.return_value = EXTRACTED_ACTIVITY
        mock_agent = MagicMock()
        mock_agent.run.return_value = {"updated_plan": new_plan, "adapt_reason": "Fatigue detected."}

        with patch("app.api.strava_client", return_value=mock_strava), \
             patch("app.api.WorkoutAgent", return_value=mock_agent):
            resp = await client.post("/api/plan/adapt")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "adapted"
        assert "pending_plan" in body

        saved = json.loads(plan_file_with_data.read_text())
        assert saved["pending_plan"] == new_plan
        assert saved["last_activity_id"] == EXTRACTED_ACTIVITY["id"]

    async def test_last_activity_id_updated_even_on_no_changes(self, client, plan_file_with_data):
        mock_strava = MagicMock()
        mock_strava.get_latest_activity.return_value = {**EXTRACTED_ACTIVITY, "id": 99999}
        mock_agent = MagicMock()
        mock_agent.run.return_value = {"updated_plan": None, "adapt_reason": "OK"}

        with patch("app.api.strava_client", return_value=mock_strava), \
             patch("app.api.WorkoutAgent", return_value=mock_agent):
            await client.post("/api/plan/adapt")

        saved = json.loads(plan_file_with_data.read_text())
        assert saved["last_activity_id"] == 99999


# ── GET /webhook (Strava subscription validation) ─────────────────────────────

class TestWebhookValidation:
    async def test_validates_correct_token(self, client):
        resp = await client.get("/webhook", params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "abc123",
        })
        assert resp.status_code == 200
        assert resp.json()["hub.challenge"] == "abc123"

    async def test_rejects_wrong_mode(self, client):
        resp = await client.get("/webhook", params={
            "hub.mode": "unsubscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "abc123",
        })
        assert resp.status_code == 400

    async def test_rejects_wrong_token(self, client):
        resp = await client.get("/webhook", params={
            "hub.mode": "subscribe",
            "hub.verify_token": "WRONG",
            "hub.challenge": "abc123",
        })
        assert resp.status_code == 403


# ── POST /webhook (Strava activity event) ────────────────────────────────────

class TestWebhookReceive:
    async def test_non_activity_event_returns_ok(self, client):
        resp = await client.post("/webhook", json={
            "object_type": "athlete",
            "aspect_type": "update",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_activity_create_without_plan_returns_no_plan(self, client_no_plan):
        resp = await client_no_plan.post("/webhook", json={
            "object_type": "activity",
            "aspect_type": "create",
            "object_id": 12345,
        })
        assert resp.json()["status"] == "no_plan"

    async def test_activity_create_with_plan_queues_adapt(self, client):
        with patch("app.api.asyncio.create_task") as mock_task:
            resp = await client.post("/webhook", json={
                "object_type": "activity",
                "aspect_type": "create",
                "object_id": 12345,
            })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_task.assert_called_once()

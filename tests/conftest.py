"""
Shared pytest fixtures used across unit and integration tests.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Minimal env so modules can import without real credentials ────────────────

os.environ.setdefault("STRAVA_CLIENT_ID", "test_client_id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("STRAVA_REFRESH_TOKEN", "test_refresh_token")
os.environ.setdefault("STRAVA_VERIFY_TOKEN", "test_verify_token")
os.environ.setdefault("GROQ_API_KEY", "test_groq_key")


# ── Sample Strava activity payloads ───────────────────────────────────────────

RAW_ACTIVITY = {
    "id": 12345,
    "name": "Morning Ride",
    "sport_type": "Ride",
    "start_date_local": "2026-04-10T07:30:00Z",
    "distance": 45000,          # 45 km
    "moving_time": 5400,        # 90 min
    "elapsed_time": 5600,
    "total_elevation_gain": 320,
    "average_speed": 8.3334,     # ≈ 30 km/h  (round(8.3334*3.6,2)==30.0)
    "average_heartrate": 148,
    "max_heartrate": 172,
    "suffer_score": 82,
    "pr_count": 2,
    "average_watts": 195,
    "kilojoules": 1053,
}

EXTRACTED_ACTIVITY = {
    "id": 12345,
    "name": "Morning Ride",
    "sport_type": "Ride",
    "date": "2026-04-10",
    "distance_km": 45.0,
    "moving_time_min": 90.0,
    "elapsed_time_min": 93.3,
    "elevation_m": 320.0,
    "avg_speed_kmh": 30.0,
    "avg_heartrate": 148,
    "max_heartrate": 172,
    "suffer_score": 82,
    "pr_count": 2,
    "avg_watts": 195,
    "kilojoules": 1053,
}


# ── Sample plan content ───────────────────────────────────────────────────────

PLAN_MD_WEEKLY = """\
## Week 1

### Monday
Easy Run — 45 min Zone 2

### Tuesday
Rest

### Wednesday
Tempo Run — 60 min with 3x10 min at Zone 4

### Thursday
Rest

### Friday
Long Run — 90 min Zone 2

### Saturday
Strength — 45 min core & mobility

### Sunday
Rest
"""

PLAN_MD_BULLET = """\
## Week of April 13th

* Monday: Warm-up 10 min, 2x20 min steady-state (Zone 3), cool-down 10 min
* Tuesday: Rest day
* Wednesday: 3x15 min high-cadence drills (Zone 4)
* Thursday: Rest day
* Friday: 60 min endurance (Zone 2)
* Saturday: Rest day
* Sunday: Event day — moderate pace (Zone 3)
"""

PLAN_JSON = {
    "objective": "Run a sub-50 min 10K",
    "plan": PLAN_MD_WEEKLY,
    "updated_at": "2026-04-10T08:00:00+00:00",
}

PLAN_JSON_WITH_PENDING = {
    **PLAN_JSON,
    "pending_plan": "## Week 1\n\n### Monday\nExtra rest — fatigue detected\n",
    "pending_updated_at": "2026-04-11T09:00:00+00:00",
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_plan_file(tmp_path):
    """Returns a Path to a temporary plan file and patches PLAN_FILE."""
    plan_file = tmp_path / "workout_plan.json"
    with patch("app.config.PLAN_FILE", plan_file), \
         patch("app.skills.PLAN_FILE", plan_file), \
         patch("app.api.PLAN_FILE", plan_file):
        yield plan_file


@pytest.fixture
def plan_file_with_data(tmp_plan_file):
    """Temporary plan file pre-populated with a valid plan."""
    tmp_plan_file.write_text(json.dumps(PLAN_JSON, indent=2))
    return tmp_plan_file


@pytest.fixture
def plan_file_with_pending(tmp_plan_file):
    """Temporary plan file pre-populated with a plan + pending plan."""
    tmp_plan_file.write_text(json.dumps(PLAN_JSON_WITH_PENDING, indent=2))
    return tmp_plan_file


@pytest.fixture
def mock_strava():
    """Mock StravaClient that returns test data without hitting the real API."""
    client = MagicMock()
    client.get_recent_activities.return_value = [EXTRACTED_ACTIVITY]
    client.get_latest_activity.return_value = EXTRACTED_ACTIVITY
    return client


@pytest.fixture
def mock_llm():
    """Mock LLM that returns a deterministic canned response."""
    llm = MagicMock()
    response = MagicMock()
    response.content = "Mocked LLM response."
    llm.invoke.return_value = response
    return llm

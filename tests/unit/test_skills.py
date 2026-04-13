"""
Unit tests for all agent skill-tools.

All Strava calls are mocked — no real API or LLM involved.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import EXTRACTED_ACTIVITY, PLAN_JSON, PLAN_MD_WEEKLY


# ── Heart rate zones ──────────────────────────────────────────────────────────

class TestHRZones:
    def _zones(self, max_hr):
        from app.skills import calculate_heart_rate_zones
        return json.loads(calculate_heart_rate_zones.invoke({"max_hr": max_hr}))

    def test_returns_five_zones(self):
        assert len(self._zones(200)) == 5

    def test_zone1_boundaries(self):
        zones = self._zones(200)
        assert zones[0]["min_bpm"] == 100   # 50%
        assert zones[0]["max_bpm"] == 120   # 60%

    def test_zone5_boundaries(self):
        zones = self._zones(200)
        assert zones[4]["min_bpm"] == 180   # 90%
        assert zones[4]["max_bpm"] == 200   # 100%

    def test_accepts_string_input(self):
        zones = self._zones("180")
        assert len(zones) == 5

    def test_zones_are_contiguous(self):
        zones = self._zones(200)
        for i in range(len(zones) - 1):
            assert zones[i]["max_bpm"] == zones[i + 1]["min_bpm"]


# ── Power zones ───────────────────────────────────────────────────────────────

class TestPowerZones:
    def _zones(self, ftp):
        from app.skills import calculate_power_zones
        return json.loads(calculate_power_zones.invoke({"ftp": ftp}))

    def test_returns_seven_zones(self):
        assert len(self._zones(250)) == 7

    def test_zone1_recovery(self):
        zones = self._zones(200)
        assert zones[0]["min_watts"] == 0
        assert zones[0]["max_watts"] == 110   # 55%

    def test_zone4_threshold_includes_ftp(self):
        zones = self._zones(200)
        z4 = zones[3]
        # Zone 4: 90–105% FTP → 180–210W
        assert z4["min_watts"] == 180
        assert z4["max_watts"] == 210

    def test_zone7_neuromuscular_has_no_upper_bound(self):
        zones = self._zones(250)
        assert zones[6]["max_watts"] == "max effort"

    def test_accepts_string_ftp(self):
        zones = self._zones("300")
        assert len(zones) == 7


# ── Race time estimator ───────────────────────────────────────────────────────

class TestEstimateRaceTime:
    def _estimate(self, distance_km, pace):
        from app.skills import estimate_race_time
        return estimate_race_time.invoke({"distance_km": distance_km, "avg_pace_min_per_km": pace})

    def test_10k_at_5min_per_km(self):
        result = self._estimate(10, 5.0)
        assert "00:50:00" in result

    def test_marathon_at_4_30_pace(self):
        result = self._estimate(42.195, 4.5)
        # 42.195 * 4.5 = 189.88 min ≈ 3h09m
        assert "03:09" in result

    def test_accepts_string_inputs(self):
        result = self._estimate("10", "6")
        assert "01:00:00" in result

    def test_output_contains_total_minutes(self):
        result = self._estimate(10, 5.0)
        assert "50.0 minutes total" in result


# ── Required pace calculator ──────────────────────────────────────────────────

class TestCalculateRequiredPace:
    def _pace(self, distance_km, target_min):
        from app.skills import calculate_required_pace
        return calculate_required_pace.invoke({
            "distance_km": distance_km,
            "target_time_min": target_min,
        })

    def test_5km_in_25_minutes_is_5min_per_km(self):
        result = self._pace(5, 25)
        assert "5:00 /km" in result

    def test_output_contains_mile_pace(self):
        result = self._pace(10, 50)
        assert "/mile" in result

    def test_output_contains_total_duration(self):
        result = self._pace(21.1, 120)
        assert "2h 0m" in result

    def test_accepts_string_inputs(self):
        result = self._pace("10", "60")
        assert "/km" in result


# ── get_weekly_volume aggregation ─────────────────────────────────────────────

class TestGetWeeklyVolume:
    def test_aggregates_by_sport_and_week(self):
        from app.skills import get_weekly_volume
        activities = [
            {**EXTRACTED_ACTIVITY, "date": "2026-04-13", "sport_type": "Ride",
             "distance_km": 30.0, "moving_time_min": 60.0},
            {**EXTRACTED_ACTIVITY, "id": 2, "date": "2026-04-12", "sport_type": "Run",
             "distance_km": 10.0, "moving_time_min": 50.0},
        ]
        with patch("app.skills._strava") as mock_client:
            mock_client.return_value.get_recent_activities.return_value = activities
            result = json.loads(get_weekly_volume.invoke({"weeks": 4}))

        sports = {b["sport"] for b in result}
        assert "Ride" in sports
        assert "Run" in sports

    def test_returns_no_activities_message_when_empty(self):
        from app.skills import get_weekly_volume
        with patch("app.skills._strava") as mock_client:
            mock_client.return_value.get_recent_activities.return_value = []
            result = get_weekly_volume.invoke({"weeks": 4})
        assert "No activities" in result


# ── save_plan validation ──────────────────────────────────────────────────────

class TestSavePlan:
    def test_rejects_unstructured_content(self, tmp_plan_file):
        from app.skills import save_plan
        result = save_plan.invoke({
            "plan": "You rode 45 km today at 30 km/h. Great effort!",
            "objective": "",
        })
        assert "ERROR" in result
        assert not tmp_plan_file.exists()

    def test_accepts_plan_with_week_headings(self, tmp_plan_file):
        from app.skills import save_plan
        result = save_plan.invoke({"plan": PLAN_MD_WEEKLY, "objective": "10K"})
        assert "Plan saved" in result
        assert tmp_plan_file.exists()
        data = json.loads(tmp_plan_file.read_text())
        assert data["plan"] == PLAN_MD_WEEKLY

    def test_accepts_plan_with_day_headings_no_week(self, tmp_plan_file):
        from app.skills import save_plan
        plan = "### Monday\nEasy run 45 min\n### Tuesday\nRest"
        result = save_plan.invoke({"plan": plan, "objective": ""})
        assert "Plan saved" in result

    def test_preserves_existing_objective_when_omitted(self, plan_file_with_data):
        from app.skills import save_plan
        result = save_plan.invoke({"plan": PLAN_MD_WEEKLY, "objective": ""})
        assert "Plan saved" in result
        data = json.loads(plan_file_with_data.read_text())
        assert data["objective"] == PLAN_JSON["objective"]

    def test_updates_objective_when_provided(self, plan_file_with_data):
        from app.skills import save_plan
        save_plan.invoke({"plan": PLAN_MD_WEEKLY, "objective": "New goal"})
        data = json.loads(plan_file_with_data.read_text())
        assert data["objective"] == "New goal"

    def test_updated_at_is_set(self, tmp_plan_file):
        from app.skills import save_plan
        save_plan.invoke({"plan": PLAN_MD_WEEKLY, "objective": "test"})
        data = json.loads(tmp_plan_file.read_text())
        assert "updated_at" in data

    def test_activity_text_does_not_overwrite_real_plan(self, plan_file_with_data):
        """Regression: LLM describing activities must not corrupt the saved plan."""
        from app.skills import save_plan
        save_plan.invoke({
            "plan": "Here are your last 3 rides: April 10 45km, April 8 30km, April 5 50km",
            "objective": "",
        })
        # Original plan should be untouched
        data = json.loads(plan_file_with_data.read_text())
        assert data["plan"] == PLAN_MD_WEEKLY


# ── get_current_plan ──────────────────────────────────────────────────────────

class TestGetCurrentPlan:
    def test_returns_plan_content(self, plan_file_with_data):
        from app.skills import get_current_plan
        result = get_current_plan.invoke({})
        assert "Run a sub-50 min 10K" in result
        assert "Monday" in result

    def test_returns_message_when_no_plan(self, tmp_plan_file):
        from app.skills import get_current_plan
        result = get_current_plan.invoke({})
        assert "No training plan" in result

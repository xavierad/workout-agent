"""
Unit tests for StravaClient._extract_stats.

No network calls — tests the pure data-transformation logic.
"""

import pytest
from tests.conftest import RAW_ACTIVITY, EXTRACTED_ACTIVITY
from app.strava import StravaClient


class TestExtractStats:
    def test_distance_converted_to_km(self):
        result = StravaClient._extract_stats(RAW_ACTIVITY)
        assert result["distance_km"] == 45.0

    def test_moving_time_converted_to_minutes(self):
        result = StravaClient._extract_stats(RAW_ACTIVITY)
        assert result["moving_time_min"] == 90.0

    def test_speed_converted_to_kmh(self):
        result = StravaClient._extract_stats(RAW_ACTIVITY)
        assert result["avg_speed_kmh"] == 30.0

    def test_date_sliced_to_yyyy_mm_dd(self):
        result = StravaClient._extract_stats(RAW_ACTIVITY)
        assert result["date"] == "2026-04-10"

    def test_elevation_rounded(self):
        result = StravaClient._extract_stats(RAW_ACTIVITY)
        assert result["elevation_m"] == 320.0

    def test_heartrate_preserved(self):
        result = StravaClient._extract_stats(RAW_ACTIVITY)
        assert result["avg_heartrate"] == 148
        assert result["max_heartrate"] == 172

    def test_power_fields_present(self):
        result = StravaClient._extract_stats(RAW_ACTIVITY)
        assert result["avg_watts"] == 195
        assert result["kilojoules"] == 1053

    def test_missing_optional_fields_are_none(self):
        minimal = {"id": 1, "distance": 0, "moving_time": 0, "elapsed_time": 0,
                   "total_elevation_gain": 0, "average_speed": 0}
        result = StravaClient._extract_stats(minimal)
        assert result["avg_heartrate"] is None
        assert result["suffer_score"] is None
        assert result["avg_watts"] is None

    def test_sport_type_falls_back_to_type_field(self):
        activity = {**RAW_ACTIVITY, "sport_type": None, "type": "VirtualRide"}
        result = StravaClient._extract_stats(activity)
        assert result["sport_type"] == "VirtualRide"

    def test_all_expected_keys_present(self):
        result = StravaClient._extract_stats(RAW_ACTIVITY)
        expected_keys = {
            "id", "name", "sport_type", "date", "distance_km", "moving_time_min",
            "elapsed_time_min", "elevation_m", "avg_speed_kmh", "avg_heartrate",
            "max_heartrate", "suffer_score", "pr_count", "avg_watts", "kilojoules",
        }
        assert expected_keys == set(result.keys())

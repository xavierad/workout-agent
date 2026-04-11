import os

import requests


class StravaClient:
    """HTTP client for the Strava API v3."""

    _API_BASE = "https://www.strava.com/api/v3"
    _TOKEN_URL = "https://www.strava.com/oauth/token"

    def __init__(self) -> None:
        self._client_id = os.environ["STRAVA_CLIENT_ID"]
        self._client_secret = os.environ["STRAVA_CLIENT_SECRET"]
        self._refresh_token = os.environ["STRAVA_REFRESH_TOKEN"]

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _get_access_token(self) -> str:
        """Exchange the refresh token for a fresh access token."""
        resp = requests.post(
            self._TOKEN_URL,
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    # ── Data extraction ───────────────────────────────────────────────────────

    @staticmethod
    def _extract_stats(activity: dict) -> dict:
        """Pull key stats from a raw Strava activity object."""
        return {
            "id": activity.get("id"),
            "name": activity.get("name"),
            "sport_type": activity.get("sport_type") or activity.get("type"),
            "date": (activity.get("start_date_local") or "")[:10],
            "distance_km": round(activity.get("distance", 0) / 1000, 2),
            "moving_time_min": round(activity.get("moving_time", 0) / 60, 1),
            "elapsed_time_min": round(activity.get("elapsed_time", 0) / 60, 1),
            "elevation_m": round(activity.get("total_elevation_gain", 0), 1),
            "avg_speed_kmh": round(activity.get("average_speed", 0) * 3.6, 2),
            "avg_heartrate": activity.get("average_heartrate"),
            "max_heartrate": activity.get("max_heartrate"),
            "suffer_score": activity.get("suffer_score"),
            "pr_count": activity.get("pr_count", 0),
            "avg_watts": activity.get("average_watts"),
            "kilojoules": activity.get("kilojoules"),
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def get_recent_activities(self, limit: int = 20) -> list[dict]:
        """Return the last *limit* activities for the authenticated athlete."""
        token = self._get_access_token()
        resp = requests.get(
            f"{self._API_BASE}/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params={"per_page": limit},
            timeout=15,
        )
        resp.raise_for_status()
        return [self._extract_stats(a) for a in resp.json()]

    def get_latest_activity(self) -> dict | None:
        """Return the most recent activity, or None if there are none."""
        activities = self.get_recent_activities(limit=1)
        return activities[0] if activities else None


# ── Module-level lazy singleton ───────────────────────────────────────────────

_client: StravaClient | None = None


def get_client() -> StravaClient:
    """Return the shared StravaClient, creating it on first call."""
    global _client
    if _client is None:
        _client = StravaClient()
    return _client

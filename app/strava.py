import os
import requests

STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"


def refresh_access_token() -> str:
    """Exchange the refresh token for a fresh access token."""
    resp = requests.post(
        STRAVA_TOKEN_URL,
        data={
            "client_id": os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


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


def get_recent_activities(limit: int = 20) -> list[dict]:
    """Return the last *limit* activities for the authenticated athlete."""
    token = refresh_access_token()
    resp = requests.get(
        f"{STRAVA_API_BASE}/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": limit},
        timeout=15,
    )
    resp.raise_for_status()
    return [_extract_stats(a) for a in resp.json()]


def get_latest_activity() -> dict | None:
    """Return the most recent activity, or None if there are none."""
    activities = get_recent_activities(limit=1)
    return activities[0] if activities else None

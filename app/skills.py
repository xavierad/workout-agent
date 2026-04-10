"""
Agent skills (tools).

Each function decorated with @tool is available to the LLM to call autonomously
during the chat. Add new skills here and they will be picked up automatically.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from langchain_core.tools import tool

from app.strava import get_client as _strava
from app.config import PLAN_FILE


# ── Strava tools ───────────────────────────────────────────────────────────────

@tool
def get_recent_activities(limit: int = 10) -> str:
    """Fetch the athlete's most recent Strava activities (up to 20).
    Returns key stats: date, sport type, distance, duration, heart rate, elevation."""
    activities = _strava().get_recent_activities(limit=min(limit, 20))
    if not activities:
        return "No activities found."
    keep = ("date", "sport_type", "distance_km", "moving_time_min",
            "elevation_m", "avg_speed_kmh", "avg_heartrate", "suffer_score")
    compact = [{k: a[k] for k in keep if a.get(k) is not None} for a in activities]
    return json.dumps(compact, indent=2)


@tool
def get_latest_activity() -> str:
    """Fetch the single most recent Strava activity with full stats."""
    activity = _strava().get_latest_activity()
    if not activity:
        return "No recent activity found."
    return json.dumps(activity, indent=2)


@tool
def get_weekly_volume(weeks: int = 4) -> str:
    """Summarise training volume per week for the last N weeks.
    Aggregates total distance (km), total duration (min), and number of sessions per sport."""
    activities = _strava().get_recent_activities(limit=50)
    if not activities:
        return "No activities found."

    now = datetime.now(timezone.utc)
    buckets: dict[str, dict] = {}
    for a in activities:
        date_str = a.get("date", "")
        if not date_str:
            continue
        try:
            date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        week_num = (now - date).days // 7
        if week_num >= weeks:
            continue
        label = f"week-{week_num}" if week_num > 0 else "this week"
        sport = a.get("sport_type", "unknown")
        key = f"{label}|{sport}"
        if key not in buckets:
            buckets[key] = {"week": label, "sport": sport,
                            "sessions": 0, "distance_km": 0.0, "duration_min": 0.0}
        buckets[key]["sessions"] += 1
        buckets[key]["distance_km"] = round(buckets[key]["distance_km"] + (a.get("distance_km") or 0), 2)
        buckets[key]["duration_min"] = round(buckets[key]["duration_min"] + (a.get("moving_time_min") or 0), 1)

    if not buckets:
        return "No activities found in the requested period."
    return json.dumps(list(buckets.values()), indent=2)


# ── Plan tools ─────────────────────────────────────────────────────────────────

@tool
def get_current_plan() -> str:
    """Read the current training plan from disk. Returns the plan text or a message if none exists."""
    if not PLAN_FILE.exists():
        return "No training plan found. The athlete should create one first."
    data = json.loads(PLAN_FILE.read_text())
    return f"Objective: {data.get('objective', 'unknown')}\nLast updated: {data.get('updated_at', 'unknown')}\n\n{data['plan']}"


@tool
def get_plan_objective() -> str:
    """Return just the athlete's training objective from the saved plan."""
    if not PLAN_FILE.exists():
        return "No training plan found."
    return json.loads(PLAN_FILE.read_text()).get("objective", "No objective set.")


# ── Training science tools ─────────────────────────────────────────────────────

@tool
def calculate_heart_rate_zones(max_hr: int) -> str:
    """Calculate the 5 heart rate training zones given the athlete's maximum heart rate.
    Zones follow the classic 5-zone model used by most endurance coaches."""
    zones = [
        ("Zone 1 – Recovery",     0.50, 0.60),
        ("Zone 2 – Aerobic base", 0.60, 0.70),
        ("Zone 3 – Tempo",        0.70, 0.80),
        ("Zone 4 – Threshold",    0.80, 0.90),
        ("Zone 5 – VO2 max",      0.90, 1.00),
    ]
    result = [{"zone": name, "min_bpm": int(max_hr * lo), "max_bpm": int(max_hr * hi)}
              for name, lo, hi in zones]
    return json.dumps(result, indent=2)


@tool
def estimate_race_time(distance_km: float, avg_pace_min_per_km: float) -> str:
    """Estimate finish time for a race given distance and average pace (min/km).
    Returns total time formatted as HH:MM:SS."""
    total_min = distance_km * avg_pace_min_per_km
    h = int(total_min // 60)
    m = int(total_min % 60)
    s = int((total_min - int(total_min)) * 60)
    return f"Estimated finish time: {h:02d}:{m:02d}:{s:02d} ({total_min:.1f} minutes total)"


@tool
def calculate_required_pace(distance_km: float, target_time_min: float) -> str:
    """Calculate the average pace (min/km and min/mile) required to finish a race in a target time."""
    pace_km = target_time_min / distance_km
    pace_mile = pace_km * 1.60934
    km_min = int(pace_km)
    km_sec = int((pace_km - km_min) * 60)
    mi_min = int(pace_mile)
    mi_sec = int((pace_mile - mi_min) * 60)
    return (f"Required pace: {km_min}:{km_sec:02d} /km  ({mi_min}:{mi_sec:02d} /mile)"
            f"\nTotal duration: {int(target_time_min//60)}h {int(target_time_min%60)}m")


@tool
def calculate_power_zones(ftp: int) -> str:
    """Calculate the 7 cycling power training zones given the athlete's Functional Threshold Power (FTP) in watts.
    Uses the classic Coggan power zone model. FTP is the average power sustainable for ~1 hour."""
    zones = [
        ("Zone 1 – Active Recovery",    0.00, 0.55),
        ("Zone 2 – Endurance",          0.55, 0.75),
        ("Zone 3 – Tempo",              0.75, 0.90),
        ("Zone 4 – Lactate Threshold",  0.90, 1.05),
        ("Zone 5 – VO2 max",            1.05, 1.20),
        ("Zone 6 – Anaerobic Capacity", 1.20, 1.50),
        ("Zone 7 – Neuromuscular",      1.50, None),
    ]
    result = []
    for name, lo, hi in zones:
        min_w = int(ftp * lo)
        max_w = int(ftp * hi) if hi is not None else None
        result.append({
            "zone": name,
            "min_watts": min_w,
            "max_watts": max_w if max_w is not None else "max effort",
        })
    return json.dumps(result, indent=2)


# ── Registry ───────────────────────────────────────────────────────────────────
# All tools the agent can use in chat. Add new @tool functions to this list.

ALL_SKILLS = [
    get_recent_activities,
    get_latest_activity,
    get_weekly_volume,
    get_current_plan,
    get_plan_objective,
    calculate_heart_rate_zones,
    calculate_power_zones,
    estimate_race_time,
    calculate_required_pace,
]

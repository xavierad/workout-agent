from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AthleteState(BaseModel):
    """Shared state flowing through the workout-planning graph."""

    # Inputs
    objective: str                             # e.g. "Run a sub-4h marathon"
    mode: str = "plan"                         # "plan" | "adapt"

    # Populated by fetch_activities node
    activities: Optional[List[Dict[str, Any]]] = None

    # Populated by analyze_fitness node
    fitness_summary: Optional[str] = None

    # Populated by create_plan / adapt_plan nodes
    current_plan: Optional[str] = None        # plan loaded from disk before adapt
    updated_plan: Optional[str] = None        # new/updated plan written to disk

    # Set before adapt_plan is called (avoids double Strava fetch)
    latest_activity: Optional[Dict[str, Any]] = None

    # Populated by adapt_plan — structured LLM decision
    needs_adaptation: Optional[bool] = None
    adapt_reason: Optional[str] = None

    # Populated by respond node
    coach_response: Optional[str] = None

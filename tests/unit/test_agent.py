"""
Unit tests for WorkoutAgent internals.

The LLM and Strava are mocked — no external calls.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from tests.conftest import EXTRACTED_ACTIVITY, PLAN_MD_WEEKLY


def make_agent(llm=None, strava=None):
    from app.agent import WorkoutAgent
    from app.strava import StravaClient

    mock_strava = strava or MagicMock(spec=StravaClient)
    mock_strava.get_recent_activities.return_value = [EXTRACTED_ACTIVITY]
    mock_strava.get_latest_activity.return_value = EXTRACTED_ACTIVITY

    if llm is None:
        mock_llm = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "Mocked LLM response."
        mock_llm.invoke.return_value = mock_resp
    else:
        mock_llm = llm

    return WorkoutAgent(mock_llm, mock_strava)


# ── _route_mode ───────────────────────────────────────────────────────────────

class TestRouteMode:
    def test_routes_plan_mode(self):
        from app.tools import AthleteState
        agent = make_agent()
        state = AthleteState(objective="10K", mode="plan")
        assert agent._route_mode(state) == "plan"

    def test_routes_adapt_mode(self):
        from app.tools import AthleteState
        agent = make_agent()
        state = AthleteState(objective="10K", mode="adapt")
        assert agent._route_mode(state) == "adapt"


# ── _fetch_activities ─────────────────────────────────────────────────────────

class TestFetchActivities:
    def test_fetches_and_stores_activities(self):
        from app.tools import AthleteState
        agent = make_agent()
        state = AthleteState(objective="10K", mode="plan")
        result = agent._fetch_activities(state)
        assert len(result["activities"]) == 1
        assert result["activities"][0]["id"] == EXTRACTED_ACTIVITY["id"]

    def test_calls_strava_with_limit_20(self):
        from app.tools import AthleteState
        mock_strava = MagicMock()
        mock_strava.get_recent_activities.return_value = []
        agent = make_agent(strava=mock_strava)
        state = AthleteState(objective="10K", mode="plan")
        agent._fetch_activities(state)
        mock_strava.get_recent_activities.assert_called_once_with(limit=20)


# ── _analyze_fitness ──────────────────────────────────────────────────────────

class TestAnalyzeFitness:
    def test_returns_fitness_summary(self):
        from app.tools import AthleteState
        mock_llm = MagicMock()
        resp = MagicMock()
        resp.content = "Athlete fitness: good aerobic base."
        mock_llm.invoke.return_value = resp
        agent = make_agent(llm=mock_llm)
        state = AthleteState(
            objective="10K", mode="plan",
            activities=[EXTRACTED_ACTIVITY],
        )
        result = agent._analyze_fitness(state)
        assert result["fitness_summary"] == "Athlete fitness: good aerobic base."

    def test_prompt_includes_activity_count(self):
        from app.tools import AthleteState
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="summary")
        agent = make_agent(llm=mock_llm)

        state = AthleteState(
            objective="10K", mode="plan",
            activities=[EXTRACTED_ACTIVITY, EXTRACTED_ACTIVITY],
        )
        agent._analyze_fitness(state)
        call_content = mock_llm.invoke.call_args[0][0][0].content
        assert "2" in call_content  # activity count mentioned in prompt


# ── _adapt_plan decision ──────────────────────────────────────────────────────

class TestAdaptPlan:
    def _make_structured_llm(self, needs_adaptation: bool, reason: str = "reason", updated_plan=None):
        from app.agent import AdaptDecision
        decision = AdaptDecision(
            needs_adaptation=needs_adaptation,
            reason=reason,
            updated_plan=updated_plan,
        )
        structured_llm = MagicMock()
        structured_llm.invoke.return_value = decision

        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = structured_llm
        return mock_llm

    def test_no_adaptation_returns_needs_adaptation_false(self):
        from app.tools import AthleteState
        llm = self._make_structured_llm(
            needs_adaptation=False,
            reason="Performance as expected.",
        )
        agent = make_agent(llm=llm)
        state = AthleteState(
            objective="10K", mode="adapt",
            fitness_summary="Good",
            current_plan=PLAN_MD_WEEKLY,
            latest_activity=EXTRACTED_ACTIVITY,
        )
        result = agent._adapt_plan(state)
        assert result["needs_adaptation"] is False
        assert result["updated_plan"] is None
        assert "expected" in result["adapt_reason"]

    def test_adaptation_needed_returns_updated_plan(self):
        from app.tools import AthleteState
        new_plan = "## Week 1\n\n### Monday\nExtra rest\n"
        llm = self._make_structured_llm(
            needs_adaptation=True,
            reason="Athlete showed fatigue.",
            updated_plan=new_plan,
        )
        agent = make_agent(llm=llm)
        state = AthleteState(
            objective="10K", mode="adapt",
            fitness_summary="Fatigued",
            current_plan=PLAN_MD_WEEKLY,
            latest_activity=EXTRACTED_ACTIVITY,
        )
        result = agent._adapt_plan(state)
        assert result["needs_adaptation"] is True
        assert result["updated_plan"] == new_plan

    def test_uses_provided_latest_activity(self):
        """If latest_activity is pre-loaded, Strava must NOT be called again."""
        from app.tools import AthleteState
        mock_strava = MagicMock()
        llm = self._make_structured_llm(needs_adaptation=False)
        agent = make_agent(llm=llm, strava=mock_strava)
        state = AthleteState(
            objective="10K", mode="adapt",
            fitness_summary="OK",
            current_plan=PLAN_MD_WEEKLY,
            latest_activity=EXTRACTED_ACTIVITY,   # pre-loaded
        )
        agent._adapt_plan(state)
        mock_strava.get_latest_activity.assert_not_called()


# ── _generate_response ────────────────────────────────────────────────────────

class TestGenerateResponse:
    def test_no_adaptation_returns_reason_directly(self):
        from app.tools import AthleteState
        agent = make_agent()
        state = AthleteState(
            objective="10K", mode="adapt",
            needs_adaptation=False,
            adapt_reason="You nailed the workout, no changes needed.",
        )
        result = agent._generate_response(state)
        assert result["coach_response"] == "You nailed the workout, no changes needed."

    def test_plan_mode_calls_llm(self):
        from app.tools import AthleteState
        mock_llm = MagicMock()
        resp = MagicMock()
        resp.content = "Great plan created!"
        mock_llm.invoke.return_value = resp
        agent = make_agent(llm=mock_llm)
        state = AthleteState(
            objective="10K", mode="plan",
            updated_plan=PLAN_MD_WEEKLY,
        )
        result = agent._generate_response(state)
        assert result["coach_response"] == "Great plan created!"
        mock_llm.invoke.assert_called_once()

"""
LangGraph workout-planning graph.
Handles plan creation and adaptation based on Strava data.
"""

import json
import textwrap

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class AdaptDecision(BaseModel):
    """Structured decision from the adapt-plan LLM call."""
    needs_adaptation: bool = Field(
        description="True if the athlete's actual performance deviates from plan expectations and the plan should change."
    )
    reason: str = Field(
        description="Concise (2–4 sentence) assessment of the performance vs. plan expectations and why the plan does or does not need changing."
    )
    updated_plan: str | None = Field(
        default=None,
        description="Full updated training plan in Markdown (required when needs_adaptation is True, null otherwise).",
    )

from app.strava import StravaClient
from app.tools import AthleteState


class WorkoutAgent:
    """LangGraph-powered workout planning and adaptation agent."""

    def __init__(self, llm, strava: StravaClient) -> None:
        self._llm = llm
        self._strava = strava
        self._graph = self._build_graph()

    # ── Public interface ──────────────────────────────────────────────────────

    def run(
        self,
        objective: str,
        mode: str = "plan",
        current_plan: str | None = None,
        latest_activity: dict | None = None,
    ) -> dict:
        """Run the planning graph and return the state dict."""
        return self._graph.invoke({
            "objective": objective,
            "mode": mode,
            "current_plan": current_plan,
            "latest_activity": latest_activity,
        })

    # ── Graph nodes ───────────────────────────────────────────────────────────

    def _fetch_activities(self, state: AthleteState) -> dict:
        print("Fetching activities from Strava...")
        activities = self._strava.get_recent_activities(limit=20)
        print(f"  → {len(activities)} activities retrieved")
        return {"activities": activities}

    def _analyze_fitness(self, state: AthleteState) -> dict:
        print("Analysing fitness...")
        prompt = textwrap.dedent(f"""
            You are an expert endurance coach and sports scientist.

            ## Athlete Activity Data ({len(state.activities)} recent sessions)
            ```json
            {json.dumps(state.activities, indent=2)}
            ```

            ## Task
            Write a concise fitness assessment (max 300 words) structured as follows:

            1. **Training Load & Weekly Volume** — total distance, time, and session frequency
            2. **Trends** — improving / plateauing / declining, and why
            3. **Strengths & Areas to Improve** — what the data shows the athlete does well and where to focus
            4. **Recovery & Readiness** — current fatigue level and readiness for hard training

            Be specific and data-driven. Reference actual numbers from the activities where relevant.
        """).strip()
        summary = self._llm.invoke([HumanMessage(content=prompt)]).content
        return {"fitness_summary": summary}

    def _create_plan(self, state: AthleteState) -> dict:
        print("Creating workout plan...")
        prompt = textwrap.dedent(f"""
            You are an expert endurance coach.

            ## Athlete Objective
            {state.objective}

            ## Fitness Assessment
            {state.fitness_summary}

            ## Task
            Design a structured progressive training plan tailored to this athlete's objective and current fitness.

            Guidelines:
            - Infer the plan duration from the objective (e.g. race in 8 weeks → 8-week plan; general fitness → 4-week rolling block)
            - Provide a day-by-day schedule (Mon–Sun) for each week
            - Specify for every session: sport, duration or distance, and intensity zone / perceived effort
            - Include a deload/recovery week at the appropriate point in the cycle
            - Open with a brief rationale explaining the chosen duration, periodisation logic, and key focus areas

            Format the entire output in clear, well-structured Markdown.
        """).strip()
        plan = self._llm.invoke([HumanMessage(content=prompt)]).content
        return {"updated_plan": plan}

    def _adapt_plan(self, state: AthleteState) -> dict:
        print("Evaluating whether plan adaptation is needed...")
        latest = state.latest_activity or self._strava.get_latest_activity()
        prompt = textwrap.dedent(f"""
            You are an expert endurance coach reviewing an athlete's latest performance.

            ## Athlete Objective
            {state.objective}

            ## Fitness Assessment
            {state.fitness_summary}

            ## Current Training Plan
            {state.current_plan}

            ## Latest Activity
            ```json
            {json.dumps(latest, indent=2)}
            ```

            ## Decision Task
            Compare the athlete's latest activity to what the plan likely called for on that day.

            Return **needs_adaptation = false** if performance was broadly in line with expectations
            (i.e. correct sport, reasonable intensity, no signs of unexpected fatigue or injury).

            Return **needs_adaptation = true** only when there is a meaningful deviation that warrants changes:
            - Significant under-performance (high HR, low pace/power, shortened session) suggesting fatigue/illness
            - Significant over-performance (well above planned intensity) suggesting the plan is too easy
            - Missed session that should shift the schedule
            - Signs of injury or excessive strain

            When needs_adaptation is true, provide a full **updated_plan** rewriting the remaining weeks.
            When needs_adaptation is false, set updated_plan to null.
        """).strip()
        structured_llm = self._llm.with_structured_output(AdaptDecision)
        decision: AdaptDecision = structured_llm.invoke([HumanMessage(content=prompt)])
        print(f"  → needs_adaptation={decision.needs_adaptation}: {decision.reason[:80]}")
        return {
            "needs_adaptation": decision.needs_adaptation,
            "adapt_reason": decision.reason,
            "updated_plan": decision.updated_plan if decision.needs_adaptation else None,
        }

    def _generate_response(self, state: AthleteState) -> dict:
        # Adapt with no changes — return the LLM's own assessment as the response
        if state.mode == "adapt" and state.needs_adaptation is False:
            return {"coach_response": state.adapt_reason}

        plan = state.updated_plan or state.current_plan or ""
        mode_label = "new plan created" if state.mode == "plan" else "plan adapted after latest activity"
        prompt = textwrap.dedent(f"""
            You are a supportive and knowledgeable endurance coach.

            ## Context
            - Athlete objective: {state.objective}
            - Status: {mode_label}

            ## Plan Summary (first 600 chars)
            {plan[:600]}

            ## Task
            In 2–3 sentences, deliver an encouraging and actionable coaching message.
            Focus on what the athlete should prioritise in their very next session.
        """).strip()
        response = self._llm.invoke([HumanMessage(content=prompt)]).content
        return {"coach_response": response}

    def _route_mode(self, state: AthleteState) -> str:
        return state.mode

    # ── Graph builder ─────────────────────────────────────────────────────────

    def _build_graph(self):
        builder = StateGraph(AthleteState)
        builder.add_node("fetch_activities", self._fetch_activities)
        builder.add_node("analyze_fitness", self._analyze_fitness)
        builder.add_node("create_plan", self._create_plan)
        builder.add_node("adapt_plan", self._adapt_plan)
        builder.add_node("generate_response", self._generate_response)

        builder.add_edge(START, "fetch_activities")
        builder.add_edge("fetch_activities", "analyze_fitness")
        builder.add_conditional_edges(
            "analyze_fitness",
            self._route_mode,
            {"plan": "create_plan", "adapt": "adapt_plan"},
        )
        builder.add_edge("create_plan", "generate_response")
        builder.add_edge("adapt_plan", "generate_response")
        builder.add_edge("generate_response", END)
        return builder.compile()

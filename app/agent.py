"""
LangGraph workout-planning graph.
Handles plan creation and adaptation based on Strava data.
"""

import json

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

from app.strava import StravaClient
from app.tools import AthleteState


class WorkoutAgent:
    """LangGraph-powered workout planning and adaptation agent."""

    def __init__(self, llm, strava: StravaClient) -> None:
        self._llm = llm
        self._strava = strava
        self._graph = self._build_graph()

    # ── Public interface ──────────────────────────────────────────────────────

    def run(self, objective: str, mode: str = "plan", current_plan: str | None = None) -> dict:
        """Run the planning graph and return the state dict."""
        return self._graph.invoke({
            "objective": objective,
            "mode": mode,
            "current_plan": current_plan,
        })

    # ── Graph nodes ───────────────────────────────────────────────────────────

    def _fetch_activities(self, state: AthleteState) -> dict:
        print("Fetching activities from Strava...")
        activities = self._strava.get_recent_activities(limit=20)
        print(f"  → {len(activities)} activities retrieved")
        return {"activities": activities}

    def _analyze_fitness(self, state: AthleteState) -> dict:
        print("Analysing fitness...")
        prompt = f"""You are an expert endurance coach and fitness analyst.
Below are the athlete's last {len(state.activities)} activities from Strava (JSON):

{json.dumps(state.activities, indent=2)}

Write a concise fitness assessment (max 300 words) covering:
1. Current training load and weekly volume
2. Trends (improving / plateauing / declining)
3. Strengths and areas to improve
4. Recovery status and readiness for hard training
"""
        summary = self._llm.invoke([HumanMessage(content=prompt)]).content
        return {"fitness_summary": summary}

    def _create_plan(self, state: AthleteState) -> dict:
        print("Creating workout plan...")
        prompt = f"""You are an expert endurance coach.
Athlete objective: {state.objective}

Recent fitness assessment:
{state.fitness_summary}

Create a structured 4-week progressive training plan tailored to this athlete.
The plan must include:
- Day-by-day workout schedule (Mon–Sun × 4 weeks)
- Specific targets per session: sport type, duration or distance, intensity zone / effort level
- A deload week in week 4
- Brief rationale for the structure

Format the output in clear Markdown.
"""
        plan = self._llm.invoke([HumanMessage(content=prompt)]).content
        return {"updated_plan": plan}

    def _adapt_plan(self, state: AthleteState) -> dict:
        print("Adapting plan based on latest activity...")
        latest = self._strava.get_latest_activity()
        prompt = f"""You are an expert endurance coach.
Athlete objective: {state.objective}

Recent fitness assessment:
{state.fitness_summary}

Current training plan:
{state.current_plan}

Latest uploaded activity:
{json.dumps(latest, indent=2)}

Analyse how the athlete performed relative to the plan, then rewrite the remaining weeks of the plan
to reflect this data. Adjust intensity, volume, or recovery days as needed.
Explain what changed and why at the top, then output the full updated plan in Markdown.
"""
        updated = self._llm.invoke([HumanMessage(content=prompt)]).content
        return {"updated_plan": updated}

    def _generate_response(self, state: AthleteState) -> dict:
        plan = state.updated_plan or state.current_plan or ""
        prompt = f"""You are a supportive, knowledgeable endurance coach.
Athlete objective: {state.objective}
Mode: {"new plan created" if state.mode == "plan" else "plan adapted after new activity"}

{plan[:600]}

In 2–3 sentences, give the athlete an encouraging and actionable message about what to focus on next.
"""
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

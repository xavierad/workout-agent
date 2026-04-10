"""
Interactive coaching chat backed by a ReAct agent with skills.
"""

import json

from langchain_core.messages import AIMessage, HumanMessage

from app.config import PLAN_FILE
from langgraph.prebuilt import create_react_agent

_SYSTEM_PROMPT = """You are an expert endurance coach and training assistant.
You have access to tools that fetch real Strava activities, read the athlete's training plan,
calculate training zones, estimate race times, and more.

Use tools proactively when questions involve data (e.g. "how did I do this week?" → call get_weekly_volume).
Be concise, specific, and encouraging. Always base advice on actual data when available.

IMPORTANT: Whenever you produce or modify a training plan, always call save_plan to persist it.

If the athlete asks to create a plan, tell them: just plan objective="<their goal>"
If the athlete asks to adapt the plan after a new activity: just adapt
"""


class CoachChat:
    """Interactive ReAct agent session for the athlete."""

    def __init__(self, llm, skills: list) -> None:
        self._agent = create_react_agent(llm, skills, prompt=_SYSTEM_PROMPT)
        self._history: list = []

    # ── Public interface ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Run the interactive chat loop until the user quits."""
        self._print_banner()

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye! Keep training hard.")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q", "bye"):
                print("Goodbye! Keep training hard.")
                break

            response, tools_used = self._send(user_input)

            if tools_used:
                print(f"\r\033[K\033[2m[used: {', '.join(tools_used)}]\033[0m")
            else:
                print("\r\033[K", end="", flush=True)

            print(f"Coach: {response}\n")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _send(self, message: str) -> tuple[str, list[str]]:
        """Append message to history, invoke agent, return (response, tools_used)."""
        self._history.append(HumanMessage(content=message))
        print("\nCoach (thinking...)", end="", flush=True)

        try:
            result = self._agent.invoke({"messages": self._history})
            ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
            response = ai_messages[-1].content if ai_messages else "(no response)"
            tool_msgs = [m for m in result["messages"]
                         if hasattr(m, "type") and m.type == "tool"]
            tools_used = list({m.name for m in tool_msgs if hasattr(m, "name")})
            self._history.append(AIMessage(content=response))
            return response, tools_used
        except Exception as e:
            self._history.pop()
            raise

    def _print_banner(self) -> None:
        from app.skills import ALL_SKILLS
        plan_objective = ""
        if PLAN_FILE.exists():
            plan_objective = json.loads(PLAN_FILE.read_text()).get("objective", "")

        print("\n" + "═" * 60)
        print("  Workout Coach — type 'quit' to exit")
        print(f"  Skills: {', '.join(s.name for s in ALL_SKILLS)}")
        print("═" * 60 + "\n")
        if plan_objective:
            print(f"Objective: {plan_objective}")
        else:
            print("No plan found. Tell me your training goal to get started.")
        print()


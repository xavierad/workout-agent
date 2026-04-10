"""
Interactive coaching chat backed by a ReAct agent with skills.
"""

import json

from langchain_core.messages import AIMessage, HumanMessage

from app.config import PLAN_FILE, build_llm
from app.skills import ALL_SKILLS
from langgraph.prebuilt import create_react_agent

SYSTEM_PROMPT = """You are an expert endurance coach and training assistant.
You have access to tools that fetch real Strava activities, read the athlete's training plan,
calculate training zones, estimate race times, and more.

Use tools proactively when questions involve data (e.g. "how did I do this week?" → call get_weekly_volume).
Be concise, specific, and encouraging. Always base advice on actual data when available.

If the athlete asks to create a plan, tell them: just plan objective="<their goal>"
If the athlete asks to adapt the plan after a new activity: just adapt
"""


def start():
    chat_llm = build_llm()
    agent = create_react_agent(chat_llm, ALL_SKILLS, prompt=SYSTEM_PROMPT)

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

    history = []

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

        history.append(HumanMessage(content=user_input))
        print("\nCoach (thinking...)", end="", flush=True)

        try:
            result = agent.invoke({"messages": history})
            ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
            response = ai_messages[-1].content if ai_messages else "(no response)"
            tool_msgs = [m for m in result["messages"]
                         if hasattr(m, "type") and m.type == "tool"]
            if tool_msgs:
                tools_used = ", ".join({m.name for m in tool_msgs if hasattr(m, "name")})
                print(f"\r\033[K\033[2m[used: {tools_used}]\033[0m")
            else:
                print("\r\033[K", end="", flush=True)
            print(f"Coach: {response}\n")
            history.append(AIMessage(content=response))
        except Exception as e:
            print(f"\n[Error: {e}]")
            history.pop()

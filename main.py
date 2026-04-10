"""
CLI entry point for the workout agent.

Commands:
  plan   --objective "<goal>"   Create a new 4-week training plan
  adapt                         Adapt the plan based on the latest Strava activity
  chat                          Interactive coaching chat with skills
"""

import argparse
import json
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from app.config import PLAN_FILE


def cmd_plan(objective: str):
    from app.agent import graph
    result = graph.invoke({"objective": objective, "mode": "plan"})
    PLAN_FILE.write_text(json.dumps({
        "objective": objective,
        "plan": result["updated_plan"],
        "updated_at": datetime.utcnow().isoformat(),
    }, indent=2))
    print("\n── TRAINING PLAN ──────────────────────────────────────────")
    print(result["updated_plan"])
    print("\n── COACH SAYS ─────────────────────────────────────────────")
    print(result["coach_response"])


def cmd_adapt():
    from app.agent import graph
    if not PLAN_FILE.exists():
        print("No existing plan found. Run `just plan objective=\"<goal>\"` first.")
        return
    data = json.loads(PLAN_FILE.read_text())
    result = graph.invoke({
        "objective": data["objective"],
        "mode": "adapt",
        "current_plan": data["plan"],
    })
    PLAN_FILE.write_text(json.dumps({
        "objective": data["objective"],
        "plan": result["updated_plan"],
        "updated_at": datetime.utcnow().isoformat(),
    }, indent=2))
    print("\n── UPDATED TRAINING PLAN ──────────────────────────────────")
    print(result["updated_plan"])
    print("\n── COACH SAYS ─────────────────────────────────────────────")
    print(result["coach_response"])


def cmd_chat():
    from app.chat import start
    start()


def main():
    parser = argparse.ArgumentParser(
        description="Workout Agent — AI-powered endurance coach",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_p = subparsers.add_parser("plan", help="Create a new 4-week training plan")
    plan_p.add_argument("--objective", required=True, help="Your training goal")

    subparsers.add_parser("adapt", help="Adapt plan after latest Strava activity")
    subparsers.add_parser("chat", help="Interactive coaching chat")

    args = parser.parse_args()

    if args.command == "plan":
        cmd_plan(args.objective)
    elif args.command == "adapt":
        cmd_adapt()
    elif args.command == "chat":
        cmd_chat()


if __name__ == "__main__":
    main()


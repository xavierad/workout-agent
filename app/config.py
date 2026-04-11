"""
Shared configuration: LLM factory and plan file path.
"""

import os
from pathlib import Path


PLAN_FILE = Path("plans/workout_plan.json")
PLAN_FILE.parent.mkdir(exist_ok=True)


def build_llm(provider: str | None = None):
    p = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()
    if p == "openai":
        from langchain_openai import ChatOpenAI
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        print(f"Using OpenAI ({model})")
        return ChatOpenAI(model=model, temperature=0)

    from langchain_groq import ChatGroq
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    print(f"Using Groq ({model})")
    return ChatGroq(model=model, temperature=0)

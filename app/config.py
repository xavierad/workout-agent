"""
Shared configuration: LLM factory and plan file path.
"""

import os
from pathlib import Path


PLAN_FILE = Path("plans/workout_plan.json")
PLAN_FILE.parent.mkdir(exist_ok=True)


def build_llm(provider: str | None = None):
    p = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()
    if p == "openai":
        from langchain_openai import ChatOpenAI
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        print(f"Using OpenAI ({model})")
        return ChatOpenAI(model=model, temperature=0)
    
    from langchain_ollama import ChatOllama
    model = os.getenv("OLLAMA_MODEL", "llama3.1")
    print(f"Using Ollama ({model})")
    return ChatOllama(
        model=model,
        base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        temperature=0,
        num_thread=int(os.getenv("OLLAMA_NUM_THREAD", "8")),
    )

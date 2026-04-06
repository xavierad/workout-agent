# Workout Agent

This repository runs an AI agent that finds and qualifies local Vancouver leads for IT services.

## Updated LangGraph Setup

The project now uses `langgraph` with a Gemini-backed `ChatOpenAI` model and structured response output.

### Installation

```bash
cd /home/xavier/workout-agent
source .venv/bin/activate
pip install -r requirements.txt
```

> If your project doesn't already have `requirements.txt`, generate it from `pyproject.toml` or install packages directly.

### Dependencies

- `langgraph>=1.1.6`
- `langchain-core>=1.2.26`
- `langchain-community>=0.4.1`
- `langchain-openai>=1.1.12`
- `python-dotenv>=1.2.2`

### Usage

1. Add your Gemini API key to `.env`.
2. Run the agent:

```bash
python main.py
```

### Files

- `main.py` — entry point that builds a LangGraph agent with tools and runs it.
- `tools.py` — defines `search`, `scrape`, and `save_to_text` tools used by the agent.
- `pyproject.toml` — project dependencies.

### Notes

- The agent is created using `langgraph.prebuilt.create_react_agent`.
- The tool names are now aligned with the prompt: `scrape`, `search`, and `save_to_text`.
- Structured output is validated using Pydantic.

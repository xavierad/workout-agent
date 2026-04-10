# Workout Agent — task runner
# Install just: https://github.com/casey/just
# Usage: just <recipe>

set dotenv-load := true

# ── Setup ──────────────────────────────────────────────────────────────────────

# Install Python dependencies
install:
    uv sync

# Install just (if not present)
install-just:
    curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to ~/.local/bin

# ── Docker ─────────────────────────────────────────────────────────────────────

# Build all Docker images
build:
    docker compose build

# Build without cache (force full rebuild)
rebuild: down
    docker compose build --no-cache

# Start webhook service (default: Groq/OpenAI)
up:
    docker compose up -d webhook

# Start webhook + Ollama (use when LLM_PROVIDER=ollama)
up-ollama:
    docker compose --profile ollama up -d

# Start with live logs
up-logs:
    docker compose up webhook

# Start with live logs + Ollama
up-logs-ollama:
    docker compose --profile ollama up

# Stop all services (keeps volumes / data)
down:
    docker compose down

# Stop all services including Ollama
down-ollama:
    docker compose --profile ollama down

# Stop and wipe all data volumes
down-clean:
    docker compose down -v

# Stop and wipe all data volumes including Ollama
down-clean-ollama:
    docker compose --profile ollama down -v

# Show service status
status:
    docker compose ps

# ── Logs ───────────────────────────────────────────────────────────────────────

# Follow all logs
logs:
    docker compose logs -f

# Follow webhook logs only
logs-webhook:
    docker compose logs -f webhook

# Follow ollama logs only
logs-ollama:
    docker compose logs -f ollama

# ── Agent CLI ──────────────────────────────────────────────────────────────────

# Create a training plan (usage: just plan objective="Run a 10K in 6 weeks")
plan objective="":
    #!/usr/bin/env sh
    if [ -z "{{objective}}" ]; then
        echo "Usage: just plan objective=\"Your training goal\""
        exit 1
    fi
    docker compose --profile cli run --rm app plan --objective "{{objective}}"

# Adapt plan based on latest Strava activity
adapt:
    docker compose --profile cli run --rm app adapt

# Start interactive coaching chat
chat:
    docker compose --profile cli run --rm app chat

# Same as above but also starts Ollama first (use when LLM_PROVIDER=ollama)
ollama-plan objective="":
    #!/usr/bin/env sh
    if [ -z "{{objective}}" ]; then
        echo "Usage: just ollama-plan objective=\"Your training goal\""
        exit 1
    fi
    docker compose --profile ollama --profile cli run --rm app plan --objective "{{objective}}"

ollama-adapt:
    docker compose --profile ollama --profile cli run --rm app adapt

ollama-chat:
    docker compose --profile ollama --profile cli run --rm app chat

# ── Docker CLI equivalents ─────────────────────────────────────────────────────

# Run plan via Docker (usage: just docker-plan objective="...")
docker-plan objective="":
    #!/usr/bin/env sh
    if [ -z "{{objective}}" ]; then
        echo "Usage: just docker-plan objective=\"Your training goal\""
        exit 1
    fi
    docker compose --profile cli run --rm app plan --objective "{{objective}}"

# Run adapt via Docker
docker-adapt:
    docker compose --profile cli run --rm app adapt

# Run chat via Docker
docker-chat:
    docker compose --profile cli run --rm app chat

# Open a shell inside the app container
shell:
    docker compose --profile cli run --rm app bash

# ── Webhook management ─────────────────────────────────────────────────────────

# Start ngrok tunnel on port 8000
ngrok:
    ngrok http 8000

# Register Strava webhook (usage: just register-webhook url=https://xxx.ngrok-free.app)
register-webhook url="":
    #!/usr/bin/env sh
    if [ -z "{{url}}" ]; then
        echo "Usage: just register-webhook url=https://<ngrok-url>"
        exit 1
    fi
    uv run scripts/register_webhook.py register --callback-url "{{url}}/webhook"

# List active Strava webhook subscriptions
list-webhooks:
    uv run scripts/register_webhook.py list

# Delete a webhook subscription (usage: just delete-webhook id=12345)
delete-webhook id="":
    uv run scripts/register_webhook.py delete --id "{{id}}"

# ── Debug ──────────────────────────────────────────────────────────────────────

# Test Strava API connectivity
test-strava:
    uv run python -c "from dotenv import load_dotenv; load_dotenv(); from app.strava import get_client; import json; print(json.dumps(get_client().get_recent_activities(limit=2), indent=2))"

# Test Ollama connectivity
test-ollama:
    curl -s http://localhost:11434/api/tags | python3 -m json.tool

# Validate imports are clean
check:
    uv run python -c "import main; print('OK')"

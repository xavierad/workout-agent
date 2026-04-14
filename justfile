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

# Start API service
up:
    docker compose up -d api

# Start with live logs
up-logs:
    docker compose up api

# Stop all services (keeps volumes / data)
down:
    docker compose down

# Stop and wipe all data volumes
down-clean:
    docker compose down -v

# Show service status
status:
    docker compose ps

# ── Logs ───────────────────────────────────────────────────────────────────────

# Follow all logs
logs:
    docker compose logs -f

# Follow API logs only
logs-api:
    docker compose logs -f api

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

# ── Frontend ──────────────────────────────────────────────────────────────────

# Install frontend dependencies
install-frontend:
    cd web && npm ci

# Run Vite dev server (proxies API to localhost:8000)
dev:
    cd web && npm run dev

# Build frontend for production
build-frontend:
    cd web && npm run build

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

# ── Tests ─────────────────────────────────────────────────────────────────────

# Run all tests
test:
    uv run pytest tests/ -v

# Run unit tests only
test-unit:
    uv run pytest tests/unit/ -v

# Run integration tests only
test-integration:
    uv run pytest tests/integration/ -v

# Run tests with coverage report
test-cov:
    uv run pytest tests/ -v --cov=app --cov-report=term-missing

# Run all tests inside the API Docker container
test-docker:
    docker compose run --rm --no-deps api uv run pytest tests/ -v

# Run unit tests inside Docker
test-docker-unit:
    docker compose run --rm --no-deps api uv run pytest tests/unit/ -v

# Run integration tests inside Docker
test-docker-integration:
    docker compose run --rm --no-deps api uv run pytest tests/integration/ -v

# ── Debug ──────────────────────────────────────────────────────────────────────

# Test Strava API connectivity
test-strava:
    uv run python -c "from dotenv import load_dotenv; load_dotenv(); from app.strava import get_client; import json; print(json.dumps(get_client().get_recent_activities(limit=2), indent=2))"

# Validate imports are clean
check:
    uv run python -c "import main; print('OK')"

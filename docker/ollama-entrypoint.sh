#!/bin/sh
set -e

# Start ollama server in background
ollama serve &
OLLAMA_PID=$!

# Wait for the server to be ready
echo "Waiting for ollama server to start..."
until ollama list > /dev/null 2>&1; do
  sleep 2
done

# Pull the model
echo "Pulling model: ${OLLAMA_MODEL}"
ollama pull "${OLLAMA_MODEL}"
echo "Model ${OLLAMA_MODEL} ready."

# Keep the server running
wait $OLLAMA_PID

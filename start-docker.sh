#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f .env ]; then
    echo "No .env file found. Copying .env.example ..."
    cp .env.example .env
    echo ""
    echo "Edit .env to configure your API keys and settings before starting."
    echo "Required: OPENROUTER_API_KEY (or equivalent for your AI provider)"
    echo "Optional: SEARCH_API_KEY (for job search)"
    echo ""
fi

echo "Starting Open Resume with Docker Compose..."

STORAGE="${STORAGE_BACKEND:-json}"

if [ "$STORAGE" = "mongodb" ]; then
    echo "Storage backend: MongoDB (enabling mongo profile)"
    docker compose --profile mongodb up -d --build
else
    echo "Storage backend: JSON files"
    docker compose up -d --build
fi

echo ""
echo "Open http://localhost:${FRONTEND_PORT:-5173}"
echo ""
echo "To stop: docker compose down"
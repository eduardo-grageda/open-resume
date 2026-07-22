#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Open Resume ==="
echo ""

if [ ! -d venv ]; then
    echo "No virtual environment found. Creating one..."
    python3 -m venv venv
    echo "Installing backend dependencies..."
    source venv/bin/activate
    pip install -r backend/requirements.txt
else
    source venv/bin/activate
fi

if [ ! -d frontend/node_modules ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd "$SCRIPT_DIR"
fi

if [ ! -f .env ]; then
    echo "No .env file found. Copying .env.example ..."
    cp .env.example .env
fi

echo "Starting backend on http://localhost:${PORT:-8000} ..."
uvicorn backend.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --reload &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:${FRONTEND_PORT:-5173} ..."
cd frontend
npx vite --host &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

echo ""
echo "Frontend: http://localhost:${FRONTEND_PORT:-5173}"
echo "Backend:  http://localhost:${PORT:-8000}"
echo "Press Ctrl+C to stop."
echo ""

cleanup() {
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "Stopped."
}

trap cleanup SIGINT SIGTERM EXIT
wait
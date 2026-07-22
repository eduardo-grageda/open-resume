#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  Open Resume — Installation"
echo "============================================"
echo ""

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        echo "ERROR: $1 is not installed. Please install $1 ($2) and try again."
        exit 1
    fi
}

check_version() {
    local cmd="$1" version_flag="$2" required="$3" label="$4"
    local version
    version=$($cmd $version_flag 2>&1 | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1)
    local major
    major=$(echo "$version" | cut -d. -f1)
    if [ "$major" -lt "$required" ]; then
        echo "ERROR: $label $version found, but $required.x+ is required."
        exit 1
    fi
    echo "  $label $version OK"
}

echo "Checking prerequisites..."

check_cmd python3 "https://python.org"
check_version python3 "--version" 3 "Python"

check_cmd node "https://nodejs.org"
check_version node "--version" 18 "Node.js"

check_cmd npm "https://nodejs.org"

echo ""

if [ ! -d venv ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "  done."
else
    echo "Virtual environment already exists, skipping creation."
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing backend dependencies..."
pip install --upgrade pip -q
pip install -r backend/requirements.txt
echo "  done."

echo ""
echo "Installing frontend dependencies..."
(
    cd frontend
    npm install
)
echo "  done."

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "  done. Edit .env to configure your AI provider API key."
else
    echo ".env already exists, skipping."
fi

if [ ! -d data ]; then
    echo "Creating data/ directory..."
    mkdir -p data
    echo "  done."
fi

echo ""
echo "============================================"
echo "  Installation complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env and set your OPENROUTER_API_KEY"
echo "  2. Run the app: ./run.sh"
echo ""
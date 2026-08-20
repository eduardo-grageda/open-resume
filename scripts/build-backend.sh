#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$HOME/.cargo/env" ]; then
  source "$HOME/.cargo/env"
fi
export PATH="$HOME/.cargo/bin:$PATH"

cd "$REPO_ROOT"

echo "=== Building Python backend with PyInstaller ==="

source venv/bin/activate

pip install pyinstaller 2>/dev/null || true

pyinstaller --clean --noconfirm backend/open-resume-backend.spec

mkdir -p src-tauri/binaries

TARGET_TRIPLE="x86_64-unknown-linux-gnu"
if command -v rustc &>/dev/null; then
    TRIPLE=$(rustc -vV | grep host | cut -d' ' -f2)
    TARGET_TRIPLE="${TRIPLE:-x86_64-unknown-linux-gnu}"
fi

cp "dist/open-resume-backend" "src-tauri/binaries/open-resume-backend-${TARGET_TRIPLE}"
chmod +x "src-tauri/binaries/open-resume-backend-${TARGET_TRIPLE}"

echo "=== Done ==="
echo "Backend binary → src-tauri/binaries/open-resume-backend-${TARGET_TRIPLE}"
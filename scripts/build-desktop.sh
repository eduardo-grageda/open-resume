#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Ensure cargo is in PATH (typical rustup install location)
if [ -f "$HOME/.cargo/env" ]; then
  source "$HOME/.cargo/env"
fi
export PATH="$HOME/.cargo/bin:$PATH"

cd "$REPO_ROOT"

echo "=== 1/3 Building Python backend ==="
bash "$SCRIPT_DIR/build-backend.sh"

echo ""
echo "=== 2/3 Building React frontend ==="
cd "$REPO_ROOT/frontend"
npm ci
npm run build
cd "$REPO_ROOT"

echo ""
echo "=== 3/3 Building Tauri desktop app ==="
cd "$REPO_ROOT"
./frontend/node_modules/.bin/tauri build
cd "$REPO_ROOT"

echo ""
echo "=== Done ==="
echo "Bundle:"
ls -lh "$REPO_ROOT/src-tauri/target/release/bundle/" 2>/dev/null || true

DEB=$(find "$REPO_ROOT/src-tauri/target/release/bundle/deb" -maxdepth 1 -name "*.deb" 2>/dev/null | head -1)
if [ -n "$DEB" ]; then
    echo ""
    ls -lh "$DEB"
fi
APPIMG=$(find "$REPO_ROOT/src-tauri/target/release/bundle/appimage" -maxdepth 1 -name "*.AppImage" 2>/dev/null | head -1)
if [ -n "$APPIMG" ]; then
    ls -lh "$APPIMG"
fi
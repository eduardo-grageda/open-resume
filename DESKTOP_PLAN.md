# DESKTOP PLAN — Open Resume: Multiplatform Desktop App

Wrap the existing React (Vite) frontend in **Tauri v2** as a native webview window. Bundle the Python/FastAPI backend as a standalone executable using **PyInstaller**. Tauri spawns the backend sidecar on launch and manages its lifecycle.

**Target platforms**: Linux (.AppImage/.deb) · Windows (.msi)
**Desktop framework**: Tauri v2
**Python bundling**: PyInstaller (onefile mode)

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Tauri v2 (Rust)                                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Native WebView Window                            │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  React/Vite Frontend (built, static)        │  │  │
│  │  │  api.js → dynamic __BACKEND_URL__           │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  main.rs:                                               │
│    1. Spawn sidecar (open-resume-backend)               │
│    2. Read PORT=<n> from stdout                         │
│    3. Poll /api/health until 200                        │
│    4. Create WebView window                             │
│    5. Inject window.__BACKEND_URL__ into page           │
│    6. On close → SIGTERM sidecar → exit                 │
└─────────────────────────────────────────────────────────┘
                           │
                    spawns / manages
                           │
┌─────────────────────────────────────────────────────────┐
│  Python Backend (PyInstaller onefile binary)            │
│                                                         │
│  main.py --port 0 --data-dir <platform-app-data>        │
│                                                         │
│  - Binds to a free OS port, prints PORT=<n> to stdout   │
│  - Data stored in OS app-data dir (not cwd)             │
│  - Handles SIGTERM for graceful shutdown                │
│  - Exposes /api/health, /api/*, /api/shutdown           │
└─────────────────────────────────────────────────────────┘
```

---

## Phase 1: Tauri v2 Setup

**Goal**: Tauri initialized in the repo, dev loop working (`npm run tauri:dev` starts backend + frontend in Tauri window).

### 1.1 Initialize Tauri in the repo

- Run `npm create tauri-app@latest` scaffolding then move `src-tauri/` to repo root, OR create manually:
  - `src-tauri/Cargo.toml` with `tauri`, `tauri-plugin-shell`, `tauri-plugin-process` deps
  - `src-tauri/build.rs` calling `tauri_build::build()`
  - `src-tauri/src/main.rs` (lib pattern via `tauri::Builder`)
  - `src-tauri/tauri.conf.json`
  - `src-tauri/icons/` (placeholder icon)
- Rust toolchain: ensure `cargo` and platform targets are installed.

### 1.2 Configure `tauri.conf.json`

```jsonc
{
  "productName": "Open Resume",
  "version": "0.1.0",
  "identifier": "com.open-resume.app",
  "build": {
    "frontendDist": "../frontend/dist",
    "devUrl": "http://localhost:5173",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  },
  "app": {
    "windows": [{
      "title": "Open Resume",
      "width": 1200,
      "height": 800,
      "minWidth": 1024,
      "minHeight": 700,
      "center": true
    }],
    "security": {
      "csp": "default-src 'self'; connect-src http://127.0.0.1:* http://localhost:*; style-src 'self' 'unsafe-inline'"
    }
  },
  "plugins": {
    "shell": {
      "sidecar": true,
      "scope": [
        {
          "name": "open-resume-backend",
          "sidecar": true
        }
      ]
    }
  }
}
```

### 1.3 Rust `main.rs` (skeleton)

```rust
fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            let shell = app.shell();
            let sidecar = shell.sidecar("open-resume-backend").unwrap();
            let (mut rx, child) = sidecar.spawn().unwrap();
            // Read PORT=<n> from stdout, poll /api/health, then resolve setup
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 1.4 Add npm scripts to `frontend/package.json`

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "tauri": "tauri",
    "tauri:dev": "tauri dev",
    "tauri:build": "tauri build"
  }
}
```

### 1.5 Update `vite.config.js` for Tauri compat

```js
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    clearScreen: false,
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### Acceptance criteria
- `npm run tauri:dev` opens a native window showing the app (backend runs separately in dev).
- Frontend loads inside the Tauri window.
- No regressions in existing `npm run dev` flow.

---

## Phase 2: Backend Adaptations

**Goal**: Backend can run as a Tauri sidecar — dynamic port, platform data dir, graceful shutdown.

### 2.1 Dynamic port binding

Add CLI arg parsing to `backend/main.py`:

```python
import argparse
import socket

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=0, help="0 = find free port")
parser.add_argument("--data-dir", type=str, default=None)
args = parser.parse_args()

port = args.port if args.port > 0 else find_free_port()
# Bind to 127.0.0.1 only (never 0.0.0.0 in desktop mode)
```

Print `PORT=<n>\n` to stdout as the first output (Tauri reads this). Then start uvicorn.

### 2.2 Platform-appropriate data directory

```python
import sys
from pathlib import Path

def get_app_data_dir() -> Path:
    if args.data_dir:
        return Path(args.data_dir)
    if sys.platform == "linux":
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.cwd()
    return base / "open-resume"
```

Pass this to config loader. All `data/` reads/writes use this path.

### 2.3 Graceful shutdown

```python
import signal

def shutdown(signum, frame):
    # Clean up scheduler, close DB connections, etc.
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)
```

### 2.4 Health endpoint

Ensure `/api/health` returns `{"status": "ok"}` (already exists from `GET /` or `GET /api/health` — verify and normalize).

### 2.5 Shutdown endpoint (backup)

```python
@router.post("/api/shutdown")
async def api_shutdown():
    os.kill(os.getpid(), signal.SIGTERM)
```

### Acceptance criteria
- `python backend/main.py --port 0` prints `PORT=XXXXX` and listens on that port.
- Data goes to `~/.local/share/open-resume/` (Linux) / `%APPDATA%\open-resume\` (Windows).
- `kill <pid>` triggers clean shutdown (scheduler stops, connections closed).

---

## Phase 3: PyInstaller Bundling

**Goal**: Produce a single `open-resume-backend` (Linux) / `open-resume-backend.exe` (Windows) binary in `src-tauri/binaries/`.

### 3.1 Create PyInstaller spec

File: `backend/open-resume-backend.spec`

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'pydantic',
        'pydantic.deprecated',
        'weasyprint',
        'pdfplumber',
        'markdown2',
        'beautifulsoup4',
        'apscheduler',
        'apscheduler.schedulers',
        'apscheduler.schedulers.asyncio',
        'curl_cffi',
        'pymongo',
        'httpx',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Collect curl_cffi's bundled libcurl
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

a.binaries += collect_dynamic_libs('curl_cffi')
a.datas += collect_data_files('curl_cffi')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='open-resume-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # True so we get stdout (PORT=<n>)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### 3.2 Build scripts

**Linux** (`scripts/build-backend.sh`):
```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source venv/bin/activate
pip install pyinstaller
pyinstaller --clean --noconfirm backend/open-resume-backend.spec
mkdir -p src-tauri/binaries
cp dist/open-resume-backend "src-tauri/binaries/open-resume-backend-x86_64-unknown-linux-gnu"
echo "Backend binary → src-tauri/binaries/"
```

**Windows** (`scripts/build-backend.ps1`):
```powershell
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."
.\venv\Scripts\Activate.ps1
pip install pyinstaller
pyinstaller --clean --noconfirm backend/open-resume-backend.spec
New-Item -ItemType Directory -Force -Path src-tauri\binaries
Copy-Item dist\open-resume-backend.exe "src-tauri\binaries\open-resume-backend-x86_64-pc-windows-msvc.exe"
Write-Host "Backend binary → src-tauri\binaries\"
```

### 3.3 Tauri sidecar naming convention

Tauri expects sidecar binaries named as `<name>-<target-triple>[.exe]`. The triples are:
- Linux: `x86_64-unknown-linux-gnu`
- Windows: `x86_64-pc-windows-msvc`

### 3.4 weasyprint risk mitigation

**Problem**: `weasyprint` depends on system GTK3/Cairo/Pango libraries. On Linux they're almost always present. On Windows they must be bundled.

**Plan A** (try first): On Windows, bundle GTK3 DLLs from a local MSYS2/Gtk installation via `--add-binary` in the spec:
```python
# Windows only: bundle GTK3 runtime
if sys.platform == 'win32':
    gtk_binaries = collect_dynamic_libs('weasyprint')
    a.binaries += gtk_binaries
```

**Plan B** (fallback if Plan A is fragile): Replace `weasyprint` with `xhtml2pdf` (pure Python, no native deps). Swap in `backend/services/pdf_export.py`:
```python
from xhtml2pdf import pisa
# Convert markdown→HTML→PDF via pisa
```
Decision deferred until we test Plan A on a Windows build.

### 3.5 curl_cffi handling

`curl_cffi` bundles a custom libcurl. PyInstaller must collect these:

```python
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files
a.binaries += collect_dynamic_libs('curl_cffi')
a.datas += collect_data_files('curl_cffi')
```
Already included in the spec above.

### Acceptance criteria
- `scripts/build-backend.sh` produces a working `open-resume-backend` binary.
- Running `./open-resume-backend --port 0` prints `PORT=XXXXX` and responds to `/api/health`.
- Binary copied to `src-tauri/binaries/` with correct target-triple name.

---

## Phase 4: Integration & Lifecycle

**Goal**: Full desktop flow — double-click app, backend starts automatically, UI loads, close window kills backend.

### 4.1 Complete `main.rs`

```rust
use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;

struct BackendState {
    port: u16,
    child: Option<tauri_plugin_shell::process::CommandChild>,
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .manage(Mutex::new(BackendState { port: 0, child: None }))
        .setup(|app| {
            let shell = app.shell();
            let sidecar_command = shell.sidecar("open-resume-backend").unwrap();
            let (mut rx, child) = sidecar_command.spawn().expect("Failed to spawn backend");

            // Read PORT=<n> from first line of stdout
            let port: u16 = loop {
                if let Some(event) = rx.blocking_recv() {
                    if let tauri_plugin_shell::process::CommandEvent::Stdout(line) = event {
                        let line_str = String::from_utf8_lossy(&line);
                        if let Some(port_str) = line_str.strip_prefix("PORT=") {
                            break port_str.trim().parse().expect("Invalid port");
                        }
                    }
                }
            };

            // Store state
            {
                let state = app.state::<Mutex<BackendState>>();
                let mut bs = state.lock().unwrap();
                bs.port = port;
                bs.child = Some(child);
            }

            // Poll health endpoint
            let health_url = format!("http://127.0.0.1:{}/api/health", port);
            let client = reqwest::blocking::Client::new();
            for _ in 0..30 {  // 30 retries × 200ms = 6s timeout
                if client.get(&health_url).send().is_ok_and(|r| r.status().is_success()) {
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(200));
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<Mutex<BackendState>>();
                if let Some(child) = state.lock().unwrap().child.take() {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 4.2 Frontend: read backend URL from Tauri

In `frontend/src/api.js`, detect the runtime environment:

```js
const BACKEND_URL = window.__BACKEND_URL__ || `http://localhost:${window.__BACKEND_PORT__ || 8000}`;

// Tauri injects these on page load:
// window.__BACKEND_PORT__ = port;  // ← injected by Tauri init script

async function request(path, options = {}) {
  const url = `${BACKEND_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}
```

### 4.3 Tauri init script injection

In `main.rs` after window creation, evaluate a JS snippet to set the port:

```rust
window.eval(&format!("window.__BACKEND_PORT__ = {};", port)).unwrap();
```

### 4.4 Error handling

- If backend binary is missing → show Tauri dialog: "Backend executable not found. Please reinstall."
- If backend fails to start (no PORT= line within 10s) → show dialog: "Failed to start backend service."
- If health check fails after 30 retries → show dialog: "Backend service is not responding."

### Acceptance criteria
- `npm run tauri:dev` (with backend running separately): app works via dev proxy.
- Production build: double-click the binary → backend starts → UI loads → close app → backend process terminates.
- No backend process left running after app closes.
- Error dialogs shown when backend is unavailable.

---

## Phase 5: Build Pipeline

**Goal**: Reproducible builds for Linux and Windows via scripts and CI.

### 5.1 Full build script

**Linux** (`scripts/build-desktop.sh`):
```bash
#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

echo "=== 1/3 Building Python backend ==="
bash scripts/build-backend.sh

echo "=== 2/3 Building React frontend ==="
cd frontend && npm ci && npm run build && cd ..

echo "=== 3/3 Building Tauri desktop app ==="
cd src-tauri && cargo tauri build && cd ..

echo "=== Done ==="
ls -lh src-tauri/target/release/bundle/
```

**Windows** (`scripts/build-desktop.ps1`):
```powershell
$ErrorActionPreference = "Stop"
$RepoRoot = (Get-Item "$PSScriptRoot\..").FullName
Set-Location $RepoRoot

Write-Host "=== 1/3 Building Python backend ==="
powershell -File scripts/build-backend.ps1

Write-Host "=== 2/3 Building React frontend ==="
Set-Location frontend
npm ci
npm run build
Set-Location $RepoRoot

Write-Host "=== 3/3 Building Tauri desktop app ==="
Set-Location src-tauri
cargo tauri build
Set-Location $RepoRoot

Write-Host "=== Done ==="
Get-ChildItem src-tauri\target\release\bundle\
```

### 5.2 GitHub Actions CI

File: `.github/workflows/desktop-release.yml`

```yaml
name: Desktop Release

on:
  push:
    tags: ['v*']
  workflow_dispatch:

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            target: x86_64-unknown-linux-gnu
            artifact: open-resume_${{ github.ref_name }}_amd64
          - os: windows-latest
            target: x86_64-pc-windows-msvc
            artifact: open-resume_${{ github.ref_name }}_x64

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Install Linux system deps
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y libwebkit2gtk-4.1-dev libgtk-3-dev \
            libcairo2-dev libpango1.0-dev libgdk-pixbuf-2.0-dev \
            libsoup-3.0-dev libjavascriptcoregtk-4.1-dev \
            librsvg2-dev libayatana-appindicator3-dev pkg-config

      - name: Install Python deps
        run: |
          python -m venv venv
          source venv/bin/activate || .\venv\Scripts\Activate.ps1
          pip install -r backend/requirements.txt pyinstaller

      - name: Build backend (PyInstaller)
        run: |
          source venv/bin/activate || .\venv\Scripts\Activate.ps1
          pyinstaller --clean --noconfirm backend/open-resume-backend.spec
          mkdir -p src-tauri/binaries
          cp dist/open-resume-backend* "src-tauri/binaries/open-resume-backend-${{ matrix.target }}"
        shell: bash

      - name: Build frontend
        run: |
          cd frontend
          npm ci
          npm run build
          cd ..

      - name: Build Tauri
        uses: tauri-apps/tauri-action@v0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          projectPath: src-tauri
          args: --target ${{ matrix.target }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: src-tauri/target/${{ matrix.target }}/release/bundle/
```

### 5.3 Linux system dependencies for Tauri

Required on Ubuntu/Debian:
```bash
sudo apt install -y \
  libwebkit2gtk-4.1-dev libgtk-3-dev libcairo2-dev \
  libpango1.0-dev libgdk-pixbuf-2.0-dev libsoup-3.0-dev \
  libjavascriptcoregtk-4.1-dev librsvg2-dev \
  libayatana-appindicator3-dev pkg-config
```

### Acceptance criteria
- `scripts/build-desktop.sh` (Linux) and `.ps1` (Windows) produce a working desktop app bundle.
- CI runs on every git tag `v*` and uploads `.deb`/`.AppImage` (Linux) and `.msi` (Windows).
- Manual trigger via `workflow_dispatch` works.

---

## Phase 6: Polish

**Goal**: Production-quality desktop experience.

### 6.1 App icon
- Source: create `app-icon.png` (1024×1024)
- Generate platform icons: `cargo tauri icon app-icon.png` (produces `.ico`, `.icns`, `.png` set)
- Place in `src-tauri/icons/`

### 6.2 Tauri bundle config

In `tauri.conf.json`, under `bundle`:
```jsonc
{
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ],
    "linux": {
      "deb": {
        "depends": ["libwebkit2gtk-4.1-0", "libgtk-3-0"]
      }
    },
    "windows": {
      "wix": {
        "language": "en-US"
      }
    }
  }
}
```

### 6.3 Window behavior
- Start maximized on first launch (or remember last size/position).
- Single instance enforcement (prevent double-launch).

### 6.4 Splash screen
- Show a loading indicator while backend starts (custom HTML splash in Tauri).
- Hide splash when health check passes.

### 6.5 Menu bar
- File: Quit
- Edit: Undo/Redo/Cut/Copy/Paste
- View: Reload, Toggle DevTools (dev only)
- Help: About

### Acceptance criteria
- App has proper icon on taskbar/dock.
- Single `.deb` installs cleanly on Ubuntu/Debian.
- `.msi` installs cleanly on Windows 10/11.
- App appears in Start Menu / app launcher.
- Splash screen shown during startup, disappears when ready.

---

## Directory Structure (Final)

```
open-resume/
├── src-tauri/                          # NEW — Tauri Rust backend
│   ├── Cargo.toml
│   ├── Cargo.lock
│   ├── tauri.conf.json
│   ├── build.rs
│   ├── capabilities/
│   │   └── default.json               # Tauri v2 capability permissions
│   ├── src/
│   │   ├── main.rs                    # App lifecycle, sidecar mgmt
│   │   └── lib.rs                     # (optional) Tauri commands
│   ├── icons/                         # Generated by `cargo tauri icon`
│   └── binaries/                      # PyInstaller outputs (gitignored)
│       ├── open-resume-backend-x86_64-unknown-linux-gnu
│       └── open-resume-backend-x86_64-pc-windows-msvc.exe
│
├── frontend/                          # Existing — React app (minor changes)
│   ├── package.json                   # MODIFIED: add tauri scripts
│   ├── vite.config.js                 # MODIFIED: Tauri compat
│   └── src/
│       └── api.js                     # MODIFIED: dynamic backend URL
│
├── backend/                           # Existing — Python app (minor changes)
│   ├── main.py                        # MODIFIED: CLI args, signal handling
│   └── open-resume-backend.spec       # NEW: PyInstaller config
│
├── scripts/                           # NEW — build automation
│   ├── build-backend.sh               # Linux backend build
│   ├── build-backend.ps1              # Windows backend build
│   ├── build-desktop.sh               # Linux full build
│   └── build-desktop.ps1              # Windows full build
│
├── .github/workflows/
│   └── desktop-release.yml            # NEW — CI/CD for multiplatform builds
│
├── DESKTOP_PLAN.md                    # This file
├── PLAIN.md                           # Original project plan
├── MEMORY.md                          # Project memory (existing)
└── ...
```

---

## Files Modified (Summary)

| File | Change |
|------|--------|
| `frontend/package.json` | Add `tauri`, `tauri:dev`, `tauri:build` scripts; add `@tauri-apps/cli` devDependency |
| `frontend/vite.config.js` | Add `strictPort`, `clearScreen`; keep proxy config |
| `frontend/src/api.js` | Dynamic `BACKEND_URL` from `window.__BACKEND_URL__` |
| `backend/main.py` | Add `--port`, `--data-dir` CLI args; port-printing; signal handlers; platform data dir |
| `backend/requirements.txt` | Add `pyinstaller` |

## Files Added (Summary)

| File | Purpose |
|------|---------|
| `src-tauri/` (entire directory) | Tauri v2 Rust project |
| `backend/open-resume-backend.spec` | PyInstaller build config |
| `scripts/build-backend.sh` | Linux backend build |
| `scripts/build-backend.ps1` | Windows backend build |
| `scripts/build-desktop.sh` | Linux full build |
| `scripts/build-desktop.ps1` | Windows full build |
| `.github/workflows/desktop-release.yml` | CI/CD pipeline |
| `DESKTOP_PLAN.md` | This plan file |

---

## Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `weasyprint` GTK3 deps on Windows | PDF export broken on Windows | Try bundling GTK3 DLLs via PyInstaller; fall back to `xhtml2pdf` (pure Python) |
| `curl_cffi` libcurl bundling | Backend won't start | `collect_dynamic_libs` + `collect_data_files` in spec (known fix) |
| Tauri sidecar stdout parsing race | Port not read before timeout | Use blocking read loop with 10s timeout; fall back to default port |
| Linux WebKit2GTK version mismatch | App won't launch on older distros | Document minimum Ubuntu 22.04+ / Debian 12+; recommend AppImage for portability |
| `apscheduler` in PyInstaller | Missing import hook | Add to `hiddenimports` list (known fix) |
| weasyprint on Linux CI | Missing system deps in CI | `apt install libcairo2-dev libpango1.0-dev ...` in CI step |

---

## Phase Progress Tracking

- [x] Phase 1: Tauri v2 Setup
- [x] Phase 2: Backend Adaptations
- [x] Phase 3: PyInstaller Bundling
- [x] Phase 4: Integration & Lifecycle
- [x] Phase 5: Build Pipeline
- [x] Phase 6: Polish

---

## Appendix A: Useful Commands

```bash
# Dev mode (backend runs separately)
source venv/bin/activate && uvicorn backend.main:app --port 8000 &
cd frontend && npm run tauri:dev

# Build backend only (Linux)
bash scripts/build-backend.sh

# Build full desktop app (Linux)
bash scripts/build-desktop.sh

# Build backend only (Windows)
powershell -File scripts/build-backend.ps1

# Build full desktop app (Windows)
powershell -File scripts/build-desktop.ps1

# Generate app icons
cd src-tauri && cargo tauri icon ../app-icon.png

# Run the bundled app
./src-tauri/target/release/open-resume
```

## Appendix B: Python Dependencies (PyInstaller Compat Notes)

| Package | PyInstaller Notes |
|---------|-------------------|
| `fastapi` / `uvicorn` | No issues, add to hiddenimports |
| `openai` | No issues |
| `pdfplumber` | Pure Python, no issues |
| `weasyprint` | **Windows: needs GTK3 DLLs** — high risk |
| `markdown2` | Pure Python, no issues |
| `beautifulsoup4` | Pure Python, no issues |
| `httpx` | Pure Python, no issues |
| `curl_cffi` | Bundles libcurl — needs `collect_dynamic_libs` |
| `pymongo` | No issues |
| `apscheduler` | No issues, add to hiddenimports |
| `pydantic` | No issues, add to hiddenimports |
| `python-multipart` | No issues |
| `python-dotenv` | No issues |
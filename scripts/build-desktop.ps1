$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Get-Item "$ScriptDir\..").FullName

Set-Location $RepoRoot

Write-Host "=== 1/3 Building Python backend ==="
& "$RepoRoot\venv\Scripts\python.exe" -m pip install pyinstaller 2>$null
& "$RepoRoot\venv\Scripts\pyinstaller.exe" --clean --noconfirm backend/open-resume-backend.spec

New-Item -ItemType Directory -Force -Path src-tauri\binaries | Out-Null
$Triple = "x86_64-pc-windows-msvc"
Copy-Item "dist\open-resume-backend.exe" "src-tauri\binaries\open-resume-backend-${Triple}.exe" -Force

Write-Host "Backend binary -> src-tauri\binaries\open-resume-backend-${Triple}.exe"
Write-Host ""

Write-Host "=== 2/3 Building React frontend ==="
Set-Location "$RepoRoot\frontend"
npm ci
npm run build
Set-Location $RepoRoot

Write-Host ""
Write-Host "=== 3/3 Building Tauri desktop app ==="
Set-Location "$RepoRoot\frontend"
npx tauri build
Set-Location $RepoRoot

Write-Host ""
Write-Host "=== Done ==="
Write-Host "Bundle:"
Get-ChildItem "$RepoRoot\src-tauri\target\release\bundle\" -ErrorAction SilentlyContinue
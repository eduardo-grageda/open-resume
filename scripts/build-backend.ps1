$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Get-Item "$ScriptDir\..").FullName

Set-Location $RepoRoot

Write-Host "=== Building Python backend with PyInstaller ==="

& "$RepoRoot\venv\Scripts\python.exe" -m pip install pyinstaller 2>$null

& "$RepoRoot\venv\Scripts\pyinstaller.exe" --clean --noconfirm backend/open-resume-backend.spec

New-Item -ItemType Directory -Force -Path src-tauri\binaries | Out-Null

$Triple = "x86_64-pc-windows-msvc"

Copy-Item "dist\open-resume-backend.exe" "src-tauri\binaries\open-resume-backend-${Triple}.exe" -Force

Write-Host "=== Done ==="
Write-Host "Backend binary → src-tauri\binaries\open-resume-backend-${Triple}.exe"
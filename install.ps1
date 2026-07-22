#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================"
Write-Host "  Open Resume — Installation"
Write-Host "============================================"
Write-Host ""

function Command-Exists($cmd) {
    return (Get-Command $cmd -ErrorAction SilentlyContinue) -ne $null
}

function Test-Version($cmd, $args, $requiredMajor, $label) {
    $output = & $cmd $args 2>&1 | Out-String
    $match = [regex]::Match($output, '(\d+)\.(\d+)(?:\.(\d+))?')
    if (-not $match.Success) {
        Write-Host "  WARNING: Could not detect $label version." -ForegroundColor Yellow
        return
    }
    $major = [int]$match.Groups[1].Value
    if ($major -lt $requiredMajor) {
        Write-Host "ERROR: $label version $major.x found, but $($requiredMajor).x+ is required." -ForegroundColor Red
        exit 1
    }
    Write-Host "  $label $($match.Value) OK"
}

Write-Host "Checking prerequisites..."

if (-not (Command-Exists "python")) {
    Write-Host "ERROR: Python is not installed." -ForegroundColor Red
    Write-Host "  Download from https://python.org (3.10+ required)"
    Write-Host "  Make sure to check 'Add Python to PATH' during installation."
    exit 1
}
Test-Version "python" @("--version") 3 "Python"

if (-not (Command-Exists "node")) {
    Write-Host "ERROR: Node.js is not installed." -ForegroundColor Red
    Write-Host "  Download from https://nodejs.org (18+ required)"
    exit 1
}
Test-Version "node" @("--version") 18 "Node.js"

if (-not (Command-Exists "npm")) {
    Write-Host "ERROR: npm is not available." -ForegroundColor Red
    exit 1
}

Write-Host ""

if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv venv
    Write-Host "  done."
} else {
    Write-Host "Virtual environment already exists, skipping creation."
}

Write-Host "Activating virtual environment..."
& "$ScriptDir\venv\Scripts\Activate.ps1"

Write-Host "Installing backend dependencies..."
python -m pip install --upgrade pip -q
python -m pip install -r "$ScriptDir\backend\requirements.txt"
Write-Host "  done."

Write-Host ""
Write-Host "Installing frontend dependencies..."
Push-Location "$ScriptDir\frontend"
npm install
Pop-Location
Write-Host "  done."

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Host "  done. Edit .env to configure your AI provider API key."
} else {
    Write-Host ".env already exists, skipping."
}

if (-not (Test-Path "data")) {
    Write-Host "Creating data\ directory..."
    New-Item -ItemType Directory -Path "data" | Out-Null
    Write-Host "  done."
}

Write-Host ""
Write-Host "============================================"
Write-Host "  Installation complete!"
Write-Host "============================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit .env and set your OPENROUTER_API_KEY"
Write-Host "  2. Start the backend:  venv\Scripts\activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
Write-Host "  3. Start the frontend: cd frontend && npm run dev"
Write-Host ""
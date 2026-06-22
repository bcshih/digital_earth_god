# start.ps1 -- Digital Earth God one-click launcher
# Usage: double-click start.bat, or right-click this file -> Run with PowerShell

$root = $PSScriptRoot

function Write-Banner {
    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor DarkYellow
    Write-Host "   Digital Earth God / MAS (TaiNan)" -ForegroundColor Yellow
    Write-Host "  ==========================================" -ForegroundColor DarkYellow
    Write-Host ""
}

function Check-Prereqs {
    if (-not (Test-Path "$root\.venv\Scripts\python.exe")) {
        Write-Host "  [ERROR] .venv not found. Please run:" -ForegroundColor Red
        Write-Host "    python -m venv .venv" -ForegroundColor Gray
        Write-Host "    .\.venv\Scripts\pip install -e '.[dev]'" -ForegroundColor Gray
        Read-Host "Press Enter to exit"
        exit 1
    }
    if (-not (Test-Path "$root\apps\web\node_modules")) {
        Write-Host "  [INFO] node_modules missing, installing..." -ForegroundColor Yellow
        Push-Location "$root\apps\web"
        npm install
        Pop-Location
    }
    if (-not (Test-Path "$root\.env")) {
        Write-Host "  [WARN] .env not found. Copy .env.example and fill in GOOGLE_API_KEY" -ForegroundColor Yellow
    }
}

Write-Banner
Check-Prereqs

# -- Swarm Server --
Write-Host "  [1/3] Starting Swarm Server (port 9000)..." -ForegroundColor Magenta
$swarmCmd = "Set-Location '$root\agents'; " +
    "Write-Host '=== DEG Swarm Server  http://localhost:9000 ===' -ForegroundColor Magenta; " +
    "..\.venv\Scripts\python -m dijizhu.swarm_server"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $swarmCmd

Start-Sleep -Seconds 3

# -- Gateway --
Write-Host "  [2/3] Starting Gateway (port 8080)..." -ForegroundColor Green
$gatewayCmd = "Set-Location '$root'; " +
    "Write-Host '=== DEG Gateway  http://localhost:8080 ===' -ForegroundColor Yellow; " +
    ".\.venv\Scripts\python -m uvicorn apps.api.gateway:app --port 8080 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $gatewayCmd

Start-Sleep -Seconds 3

# -- Frontend --
Write-Host "  [3/3] Starting Frontend (port 3000)..." -ForegroundColor Cyan
$frontendCmd = "Set-Location '$root\apps\web'; " +
    "Write-Host '=== DEG Frontend  http://localhost:3000 ===' -ForegroundColor Cyan; " +
    "npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# -- Open browser --
Write-Host ""
Write-Host "  Waiting 10 seconds for services to start..." -ForegroundColor Gray
Start-Sleep -Seconds 10
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor DarkGray
Write-Host "   Gateway    http://localhost:8080" -ForegroundColor Gray
Write-Host "   Frontend   http://localhost:3000" -ForegroundColor Gray
Write-Host "   Explore    http://localhost:3000/" -ForegroundColor Gray
Write-Host "   Wish       http://localhost:3000/wish" -ForegroundColor Gray
Write-Host "   Dashboard  http://localhost:3000/dashboard" -ForegroundColor Gray
Write-Host "   Offline    http://localhost:3000/demo" -ForegroundColor Gray
Write-Host "  ==========================================" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  This window can be closed. Services run in their own windows." -ForegroundColor DarkGray
Write-Host ""
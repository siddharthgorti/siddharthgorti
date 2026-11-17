# One-command local demo for Windows: sets up, builds and runs Tailored Tuition.
#
# Usage (in PowerShell, from the tailored-tuition folder):
#     powershell -ExecutionPolicy Bypass -File .\demo.ps1
# Stop with Ctrl+C.
#
# Written for Windows PowerShell 5.1 (built into Windows 10/11) and PowerShell 7.
# Keep this file ASCII-only: PowerShell 5.1 misreads non-ASCII characters in BOM-less files.

# Native tools (pip, npm) report failure through exit codes, which PowerShell 5.1
# does not treat as errors, so every step checks $LASTEXITCODE explicitly.
$ErrorActionPreference = "Continue"
$Root = $PSScriptRoot
Set-Location $Root

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

# --- Ports -------------------------------------------------------------------
foreach ($port in 3000, 8000) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Fail "Port $port is already in use. Is the demo already running in another window? Close it and try again."
    }
}

# --- Python (3.12 to 3.14; 3.13 preferred) ------------------------------------
# Brand-new Python releases often lack prebuilt packages for some dependencies,
# which then fail to install on Windows, so we pick a known-good version.
$VenvPython = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        Fail "Python not found. Install Python 3.13 from https://www.python.org/downloads/ , then open a NEW PowerShell window and run this again."
    }
    $PyVersion = $null
    foreach ($v in "3.13", "3.12", "3.14") {
        & py "-$v" -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $PyVersion = $v; break }
    }
    if (-not $PyVersion) {
        Fail "Python 3.12, 3.13 or 3.14 is required. Install Python 3.13 from https://www.python.org/downloads/ , then run this again."
    }
    Step "Creating Python environment (Python $PyVersion)"
    & py "-$PyVersion" -m venv (Join-Path $Root "backend\.venv")
    if ($LASTEXITCODE -ne 0) { Fail "Could not create the Python environment." }
}

Step "Installing backend packages"
& $VenvPython -m pip install --disable-pip-version-check -q -r (Join-Path $Root "backend\requirements.txt")
if ($LASTEXITCODE -ne 0) { Fail "Installing Python packages failed (see the messages above)." }

$EnvFile = Join-Path $Root "backend\.env"
if (-not (Test-Path $EnvFile)) { Copy-Item (Join-Path $Root "backend\.env.example") $EnvFile }
# Which AI the tutor will use: Claude (API key), else a local Ollama model, else canned demo replies.
$HasKey = Select-String -Path $EnvFile -Pattern '^ANTHROPIC_API_KEY=.+' -Quiet
$OllamaUp = $false
try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://localhost:11434/api/tags" | Out-Null; $OllamaUp = $true } catch { }
if ($HasKey) {
    $AiMode = "Claude (Anthropic API key found)"
} elseif ($OllamaUp) {
    $AiMode = "LOCAL model via Ollama (free; weaker at maths and slower than Claude)"
} else {
    $AiMode = "OFFLINE DEMO - canned replies, no real tutoring"
    Write-Host "    No API key and Ollama isn't running, so the tutor will NOT really tutor." -ForegroundColor Yellow
    Write-Host "    For real tutoring, either:" -ForegroundColor Yellow
    Write-Host "      - free: install Ollama (https://ollama.com), run: ollama pull qwen2.5:7b , then re-run this" -ForegroundColor Yellow
    Write-Host "      - best: add ANTHROPIC_API_KEY=sk-ant-... to backend\.env and re-run this" -ForegroundColor Yellow
}

# --- Node ----------------------------------------------------------------------
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Fail "Node.js not found. Install the LTS version from https://nodejs.org/ , then open a NEW PowerShell window and run this again."
}
$NodeMajor = [int]((& node -v).TrimStart("v").Split(".")[0])
if ($NodeMajor -lt 20) { Fail "Node.js 20 or newer is required (you have $(& node -v)). Install the LTS version from https://nodejs.org/" }

Push-Location (Join-Path $Root "frontend")
if (-not (Test-Path node_modules)) {
    Step "Installing frontend packages (first run only, a few minutes)"
    & npm ci --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { Pop-Location; Fail "Installing frontend packages failed (see the messages above)." }
}
Step "Building the website"
$BuildOutput = & npm run build 2>&1
if ($LASTEXITCODE -ne 0) { $BuildOutput | Write-Host; Pop-Location; Fail "Building the website failed (see the messages above)." }
Pop-Location

# --- Start -----------------------------------------------------------------------
Step "Starting"
$Backend = Start-Process -PassThru -NoNewWindow `
    -WorkingDirectory (Join-Path $Root "backend") `
    -FilePath $VenvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"

$Ready = $false
for ($i = 0; $i -lt 30; $i++) {
    if ($Backend.HasExited) { break }
    try {
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:8000/api/health" | Out-Null
        $Ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $Ready) {
    Stop-Process -Id $Backend.Id -ErrorAction SilentlyContinue
    Fail "The backend did not start (see the messages above)."
}

# Address for phones: the IPv4 address of the adapter that has the default route.
$Ip = $null
$Category = $null
$Route = Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -First 1
if ($Route) {
    $Ip = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $Route.ifIndex -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress
    $Category = (Get-NetConnectionProfile -InterfaceIndex $Route.ifIndex -ErrorAction SilentlyContinue).NetworkCategory
}

Write-Host ""
Write-Host "  Tutor AI: $AiMode" -ForegroundColor Cyan
Write-Host "  On this computer:          http://localhost:3000" -ForegroundColor Green
if ($Ip) { Write-Host "  On a phone (same Wi-Fi):   http://${Ip}:3000" -ForegroundColor Green }
Write-Host ""
Write-Host "  If Windows asks whether to allow Node.js, tick 'Private networks' and click Allow."
if ("$Category" -eq "Public") {
    Write-Host "  Your Wi-Fi is set to 'Public', so Windows will block phones. To allow them:" -ForegroundColor Yellow
    Write-Host "  Settings > Network & internet > Wi-Fi > (your network) > Network profile type: Private." -ForegroundColor Yellow
}
Write-Host "  Stop with Ctrl+C."
Write-Host ""

try {
    Set-Location (Join-Path $Root "frontend")
    # Run Next's entry script with node directly: going through npx.cmd would
    # make Ctrl+C ask "Terminate batch job (Y/N)?".
    & node "node_modules\next\dist\bin\next" start -H 0.0.0.0 -p 3000
} finally {
    Stop-Process -Id $Backend.Id -ErrorAction SilentlyContinue
    Set-Location $Root
}

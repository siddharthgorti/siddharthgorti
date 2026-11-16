# One-command local demo (Windows PowerShell): sets up, builds and runs Tailored Tuition.
# Usage (in PowerShell, from this folder):  powershell -ExecutionPolicy Bypass -File .\demo.ps1
# Stop with Ctrl+C.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Install Python 3.12+ from https://www.python.org/downloads/ (tick 'Add to PATH')." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Install Node.js 22 LTS from https://nodejs.org/" }

foreach ($port in 3000, 8000) {
  if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $port is already in use (is the demo already running in another window?). Close it and try again."
  }
}

Write-Host "==> Backend setup"
if (-not (Test-Path backend\.venv)) { py -3 -m venv backend\.venv }
& backend\.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt
if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (-not (Select-String -Path backend\.env -Pattern '^ANTHROPIC_API_KEY=.+' -Quiet)) {
  Write-Host "    No API key in backend\.env: running in OFFLINE DEMO MODE (canned replies)."
  Write-Host "    For real tutoring, add ANTHROPIC_API_KEY=sk-ant-... to backend\.env and re-run."
}

Write-Host "==> Frontend setup (first run takes a few minutes)"
Push-Location frontend
if (-not (Test-Path node_modules)) { npm ci --no-audit --no-fund }
npm run build | Out-Null
Pop-Location

Write-Host "==> Starting"
$backend = Start-Process -PassThru -NoNewWindow -WorkingDirectory backend `
  -FilePath "$PSScriptRoot\backend\.venv\Scripts\python.exe" `
  -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000","--log-level","warning"
try {
  $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -eq "Dhcp" } | Select-Object -First 1).IPAddress
  Write-Host ""
  Write-Host "  On this computer:  http://localhost:3000"
  if ($ip) { Write-Host "  On a phone (same Wi-Fi):  http://${ip}:3000" }
  Write-Host "  Stop with Ctrl+C"
  Write-Host ""
  Set-Location frontend
  npx next start -H 0.0.0.0 -p 3000
} finally {
  Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
}

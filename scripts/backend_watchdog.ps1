# Backend watchdog for the ANUMAAN demo. Polls /api/health every few seconds and, only if the
# backend is actually unreachable (not just slow), relaunches it under the same Python 3.12
# interpreter that has kokoro/pywhispercpp installed (see scripts/check_backend_health.ps1 and
# the session notes on why the backend must run under 3.12, not the system-default 3.14, for
# voice to work). Never touches a backend that's already responding, so it's safe to leave
# running throughout the demo without risking the current warm STT/TTS/LLM state.

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$python312 = "C:\Users\Prasad\AppData\Local\Programs\Python\Python312\python.exe"
$healthUrl = "http://127.0.0.1:8000/api/health"
$pollSeconds = 5

Write-Host "[Watchdog] Monitoring $healthUrl every ${pollSeconds}s. Ctrl+C to stop."

while ($true) {
    $healthy = $false
    try {
        $resp = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 3 -UseBasicParsing
        if ($resp.StatusCode -eq 200) { $healthy = $true }
    } catch {
        $healthy = $false
    }

    if (-not $healthy) {
        Write-Host "[Watchdog] $(Get-Date -Format 'HH:mm:ss') Backend unreachable -- restarting..."
        Get-Process -Name python -ErrorAction SilentlyContinue |
            Where-Object { (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine -match "uvicorn backend.server.main" } |
            Stop-Process -Force -ErrorAction SilentlyContinue

        Start-Sleep -Seconds 1
        Start-Process -FilePath $python312 `
            -ArgumentList "-m", "uvicorn", "backend.server.main:app", "--host", "127.0.0.1", "--port", "8000" `
            -WorkingDirectory $repoRoot `
            -WindowStyle Normal
        Write-Host "[Watchdog] Restart issued. Waiting for it to come back up..."
        Start-Sleep -Seconds 10
    }

    Start-Sleep -Seconds $pollSeconds
}

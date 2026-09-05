@echo off
setlocal enabledelayedexpansion
title ROTAX 912 iS DIGITAL TWIN - LAPTOP BACKEND SERVER (DRDO PS-26054)

echo ===============================================================================
echo   ROTAX 912 iS MALE UAV DIGITAL TWIN - LAPTOP BACKEND SERVER
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.

cd /d "%~dp0"

rem Forces Python's stdout/stderr to UTF-8 regardless of the console's legacy code page.
rem Without this, a bare console (this .bat double-clicked -> cmd.exe with the default
rem OEM/ANSI code page, NOT UTF-8) makes any print()/log of a non-ASCII character (an em
rem dash or checkmark in a manual name, an AI-generated reply, etc.) raise an uncaught
rem UnicodeEncodeError. Confirmed by direct repro on this machine: with PYTHONUTF8 unset,
rem `python -c "print('check ✅')"` crashes; with it set to 1, it prints cleanly. A crash
rem during document loading happens inside EngineStateService.__init__(), which FastAPI's
rem startup calls synchronously - so this exact crash takes down the ENTIRE backend
rem (telemetry included) before the server ever starts serving.
set PYTHONUTF8=1

echo [1/3] Checking Python environment...
python -c "import fastapi, uvicorn, websockets, pydantic; print('  [OK] Dependencies verified.')" 2>nul
if %errorlevel% neq 0 (
    echo [!] Installing required server dependencies...
    pip install -r requirements.txt
)

echo.
echo [2/3] Checking port 8000 is free...
rem A standalone .ps1 (see scripts/check_backend_port.ps1 for why) rather than an inline
rem `powershell -Command "..."` one-liner, which broke under this file's `enabledelayedexpansion`.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check_backend_port.ps1"

echo.
echo [3/3] Launching Authoritative 20 Hz Telemetry and Control Server...
echo   - Local REST API:      http://127.0.0.1:8000
echo   - Interactive Swagger: http://127.0.0.1:8000/docs
echo   - Mobile Telemetry WS: ws://127.0.0.1:8000/ws/telemetry
echo   - Blender Twin WS:     ws://127.0.0.1:8000/ws/blender
echo.
echo   * Connect your Mobile Phone to whichever of these matches your phone's network:
powershell -NoProfile -Command "Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } | ForEach-Object { Write-Host ('      - ' + $_.InterfaceAlias + ': http://' + $_.IPv4Address.IPAddress + ':8000') }"
echo.
echo -------------------------------------------------------------------------------

uvicorn backend.server.main:app --host 0.0.0.0 --port 8000

pause

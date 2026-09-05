@echo off
title ROTAX 912 iS SPORT — 3D DIGITAL TWIN VISUALIZATION CLIENT
color 0B

echo ===============================================================================
echo   ROTAX 912 iS SPORT MALE UAV DIGITAL TWIN - 3D BLENDER VISUALIZATION CLIENT
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.

rem See launch_backend_server.bat for why: forces UTF-8 stdout/stderr for Blender's bundled
rem Python too, so a non-ASCII character anywhere (AI diagnosis text, manual titles) can't
rem crash the embedded script with an uncaught UnicodeEncodeError on a legacy-codepage console.
set PYTHONUTF8=1

set "BLENDER_EXE="

if exist "E:\Blender\blender.exe" set "BLENDER_EXE=E:\Blender\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
if not defined BLENDER_EXE (
    where blender >nul 2>nul
    if not errorlevel 1 set "BLENDER_EXE=blender"
)

if not defined BLENDER_EXE (
    echo [ERROR] Blender engine executable not found!
    pause
    exit /b 1
)

echo [1/2] Checking Laptop Backend Server status on port 8000...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2 -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Backend server not detected - launching it now in a separate window...
    start "ROTAX BACKEND SERVER" cmd /k "%~dp0launch_backend_server.bat"
    echo [INFO] Waiting for the backend to initialize...
    timeout /t 5 /nobreak >nul
) else (
    echo [OK] Backend server already running.
)

echo [2/2] Connecting to Laptop Backend Server (http://127.0.0.1:8000)...
echo [NOTE] If telemetry is offline, ensure launch_backend_server.bat is running.
echo [OK] Launching Dedicated 3D Digital Twin Client (EEVEE Viewport Mode)...
echo.

"%BLENDER_EXE%" "%~dp03d_models\rotax_912_is_sport.blend" --python "%~dp0apps\blender_twin\standalone_digital_twin_app.py"

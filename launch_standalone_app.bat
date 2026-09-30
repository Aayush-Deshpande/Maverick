@echo off
chcp 65001 >nul
title ANUMAAN - 3D DIGITAL TWIN FAULT DIAGNOSTIC COCKPIT
color 0B

echo ===============================================================================
echo   ROTAX 912 iS SPORT - 3D DIGITAL TWIN FAULT DIAGNOSTIC COCKPIT
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.
echo Controls:
echo   [1]-[8] Direct Fault Injection and Glowing Component Isolation (Orange/Red)
echo   [0]     Reset to Nominal Flight Mode (Authentic Solid PBR Render)
echo   [SPACE] Toggle Turntable Orbit
echo   [G]     Toggle Holographic Ghost X-Ray Vision
echo   [TAB/H] Toggle Aerospace Cockpit HUD
echo.

set "PYTHONUTF8=1"

rem 1. Resolve 3D blend model (Rotax 912 iS Sport 109-mesh model)
set "TARGET_BLEND=%~dp0assets\blender\rotax_912_is_sport.blend"
if not exist "%TARGET_BLEND%" set "TARGET_BLEND=%~dp0assets\blender\rotax_912is_showcase.blend"
if not exist "%TARGET_BLEND%" set "TARGET_BLEND=%~dp0assets\blender\anumaan_master_twin.blend"

if not exist "%TARGET_BLEND%" (
    echo [ERROR] No 3D model file found!
    pause
    exit /b 1
)

echo [3D ASSET]  Model: %TARGET_BLEND%
echo.

set "BLENDER_EXE="
if exist "D:\Blender\blender.exe" set "BLENDER_EXE=D:\Blender\blender.exe"
if not defined BLENDER_EXE if exist "E:\Blender\blender.exe" set "BLENDER_EXE=E:\Blender\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
if not defined BLENDER_EXE (
    where blender >nul 2>nul
    if not errorlevel 1 set "BLENDER_EXE=blender"
)

if not defined BLENDER_EXE (
    echo [ERROR] Blender not found!
    pause
    exit /b 1
)

echo [BLENDER]   %BLENDER_EXE%
echo.

echo [1/2] Checking Backend Server on port 8000...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check_backend_health.ps1" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Backend offline - Autonomous Digital Twin Mode.
) else (
    echo [OK] Backend connected - 20 Hz live telemetry active.
)

set "SCRIPT_PATH=%~dp0apps\blender_twin\standalone_fault_diagnostic_app.py"
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] Python script not found: %SCRIPT_PATH%
    pause
    exit /b 1
)

echo [2/2] Launching Blender 3D Fault Diagnostic Twin...
echo.
echo   Console stays open. Close Blender to exit.
echo.

"%BLENDER_EXE%" "%TARGET_BLEND%" --python "%SCRIPT_PATH%"

echo.
echo Blender exited. Check output above for errors.
pause
@echo off
title TOP GUN: MAVERICK — LADAKH CANYON UAV TACTICAL FLIGHT SIMULATOR
color 0B

echo ===============================================================================
echo   TOP GUN: MAVERICK // LADAKH CANYON UAV FLIGHT SIMULATOR (NATIVE BLENDER)
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.

rem See launch_backend_server.bat for why: forces UTF-8 stdout/stderr for Blender's bundled
rem Python too, so a non-ASCII character anywhere can't crash the embedded script with an
rem uncaught UnicodeEncodeError on a legacy-codepage console.
set PYTHONUTF8=1

set BLENDER_EXE=""

if exist "D:\Blender\blender.exe" (
    set BLENDER_EXE="D:\Blender\blender.exe"
) else if exist "E:\Blender\blender.exe" (
    set BLENDER_EXE="E:\Blender\blender.exe"
) else if exist "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" (
    set BLENDER_EXE="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
) else if exist "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" (
    set BLENDER_EXE="C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
) else if exist "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" (
    set BLENDER_EXE="C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
) else (
    where blender >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set BLENDER_EXE=blender
    )
)

if %BLENDER_EXE%=="" (
    echo [ERROR] Blender executable not found!
    pause
    exit /b 1
)

echo [OK] Launching Canyon Flight Simulator V2 - Real-Time Physics Engine...
echo [OK] Physics-driven UAV, Chase camera behind tail, Auto-GCAS armed
echo [OK] Controls: W/S=Pitch  A/D=Turn  E/Q=Throttle  7/8/9/0=Presets (140/180/234/264kt)  C=Copilot  R=Reset  ESC=Exit
echo.

%BLENDER_EXE% --window-maximized "%~dp0assets\models\terrain.blend" --python "%~dp0apps\blender_twin\standalone_canyon_flight_app.py"

echo.
echo [SIM] Blender process exited. If it closed instantly, review the error above.
pause

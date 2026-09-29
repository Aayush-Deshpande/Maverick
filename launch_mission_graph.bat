@echo off
title MISSION KNOWLEDGE GRAPH - 3D POST-MISSION ANALYTICS EXPLORER
color 0B

echo ===============================================================================
echo   MISSION KNOWLEDGE GRAPH // 3D POST-MISSION ANALYTICS EXPLORER
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.

rem Same rationale as launch_canyon_simulation.bat: force UTF-8 for Blender's bundled
rem Python so a degree sign or delta in a report can't crash the embedded script on a
rem legacy-codepage console.
set PYTHONUTF8=1

if not exist "%~dp0report_dump" (
    echo [WARN] report_dump\ not found - no missions to display.
    echo        Generate some with:  python scripts\simulate_missions.py
    echo.
)

set BLENDER_EXE=""

if exist "D:\Blender\blender.exe" (
    set BLENDER_EXE="D:\Blender\blender.exe"
) else if exist "D:\Blender\blender.exe" (
    set BLENDER_EXE="D:\Blender\blender.exe"
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

echo [OK] Launching Mission Knowledge Graph Explorer...
echo [OK] LMB DRAG Orbit  ^|  LMB Open node  ^|  WHEEL Zoom  ^|  ESC Back  ^|  R Rescan
echo.

rem --factory-startup guarantees a clean scene and no user add-ons competing for the
rem viewport; the app draws its own world and needs nothing from a .blend file.
%BLENDER_EXE% --factory-startup --python "%~dp0apps\mission_graph_viewer\standalone_mission_graph_app.py"

echo.
echo [GRAPH] Blender process exited. If it closed instantly, review the error above.
pause

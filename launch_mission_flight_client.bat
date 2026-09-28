@echo off
title ANUMAAN — MISSION FLIGHT CLIENT (BLENDER VISUAL COCKPIT)
color 0B

echo ===============================================================================
echo   ANUMAAN MISSION FLIGHT CLIENT — Live Visual Cockpit for the Web Mission Planner
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.
echo [INFO] This window is a READ-ONLY visualizer of the mission running on the backend.
echo [INFO] Plan / launch / inject faults / derate / divert from the WEB APP.
echo [INFO] Requires the backend server already running at http://127.0.0.1:8000
echo        with a mission loaded and started (Mission Operations -^> Launch).
echo.

set PYTHONUTF8=1
set BLENDER_EXE=""

if exist "D:\Blender\blender.exe" (
    set BLENDER_EXE="D:\Blender\blender.exe"
) else if exist "E:\Blender\blender.exe" (
    set BLENDER_EXE="E:\Blender\blender.exe"
) else if exist "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" (
    set BLENDER_EXE="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
) else (
    where blender >nul 2>nul
    if %ERRORLEVEL% equ 0 set BLENDER_EXE=blender
)

if %BLENDER_EXE%=="" (
    echo [ERROR] Blender executable not found!
    pause
    exit /b 1
)

%BLENDER_EXE% --window-maximized "%~dp0assets\models\terrain.blend" --python "%~dp0apps\blender_twin\mission_flight_client.py"

echo.
echo [SIM] Blender process exited.
pause

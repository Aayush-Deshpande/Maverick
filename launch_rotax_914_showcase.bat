@echo off
chcp 65001 >nul
title Launch Rotax 914 F Turbo Technical Showcase Digital Twin
color 0B
echo ===============================================================================
echo   ROTAX 914 F TURBOCHARGED // 3D TECHNICAL SHOWCASE & SUBSYSTEM INSPECTOR
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.
echo Controls:
echo   [1] Prop Reduction Gearbox & Aircraft Flange
echo   [2] Dual Induction Manifold & Composite Airbox
echo   [3] Stainless Equal-Length Scavenging Exhaust Runners
echo   [4] Integrated Garrett Turbocharger & Servomotor Wastegate
echo   [5] Rotax TCU & Real-Time Digital Twin Suite
echo   [0] Reset to Full Assembly (or ESC)
echo   [F1]-[F5] Switch Engines anytime in-session
echo.

set "PYTHONUTF8=1"
set "ANUMAAN_ENGINE_ID=rotax_914"
set "TARGET_BLEND=%~dp0assets\blender\anumaan_master_twin.blend"

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

start "" "%BLENDER_EXE%" "%TARGET_BLEND%" --python "%~dp0apps\blender_twin\standalone_digital_twin_app.py"

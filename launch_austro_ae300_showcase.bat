@echo off
chcp 65001 >nul
title Launch Austro AE300 CRDi Turbodiesel Showcase Digital Twin
color 0B
echo ===============================================================================
echo   AUSTRO ENGINE AE300 / AE330 // 3D TECHNICAL SHOWCASE ^& SUBSYSTEM INSPECTOR
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.
echo Controls:
echo   [1] Reduction Gearbox ^& Dual-Mass Flywheel
echo   [2] 1,600 bar Common Rail Injection ^& Bosch HP Radial Pump
echo   [3] Cast Stainless Exhaust Collector ^& Inconel Heat Blanket
echo   [4] Variable Geometry Turbocharger (VGT) ^& Charge Intercooler
echo   [5] Dual-Channel EECU FADEC ^& Single-Power Lever Management
echo   [0] Reset to Full Assembly (or ESC)
echo   [F1]-[F5] Switch Engines anytime in-session
echo.

set "PYTHONUTF8=1"
set "ANUMAAN_ENGINE_ID=austro_ae300"
set "TARGET_BLEND=%~dp0assets\blender\anumaan_master_twin.blend"

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
    echo [ERROR] Blender engine executable not found!
    pause
    exit /b 1
)

start "" "%BLENDER_EXE%" "%TARGET_BLEND%" --python "%~dp0apps\blender_twin\standalone_digital_twin_app.py"

@echo off
chcp 65001 >nul
title ANUMAAN — 3D DIGITAL TWIN VISUALIZATION CLIENT
color 0B

echo ===============================================================================
echo   ANUMAAN - MULTI-ENGINE MALE UAV 3D DIGITAL TWIN VISUALIZATION CLIENT
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.

set PYTHONUTF8=1

rem 1. Check if engine argument was passed
if not "%~1"=="" set "ANUMAAN_ENGINE_ID=%~1"

rem 2. Interactive engine menu if not preset
if "%ANUMAAN_ENGINE_ID%"=="" (
    echo Select Initial Engine Digital Twin to visualize:
    echo   [1] Rotax 912 iS Sport   (100 hp Naturally Aspirated EFI)
    echo   [2] Rotax 914 F Turbo    (115 hp Turbocharged TCU)
    echo   [3] Rotax 915 iS A       (141 hp Turbo Intercooled FADEC)
    echo   [4] Austro Engine AE300  (170/180 hp Common-Rail Turbo Diesel)
    echo   [5] VRDE / JAYEM 2.2L    (180 hp Indigenous DRDO CRDi Diesel)
    echo.
    echo   [NOTE] You can switch engines anytime in-app using keys [F1] to [F5]!
    echo   [NOTE] Press [1]-[5] to Inspect Subsystems (Ghost Isolation + HUD Specs)!
    echo   [NOTE] Press [0] or [ESC] to Reset to Full Assembly!
    echo.
    choice /c 12345 /t 4 /d 1 /m "Select initial engine [1-5] (Auto-selects [1] in 4s): "
    if errorlevel 5 set "ANUMAAN_ENGINE_ID=vrde_jayem_2_2l"
    if errorlevel 4 if not defined ANUMAAN_ENGINE_ID set "ANUMAAN_ENGINE_ID=austro_ae300"
    if errorlevel 3 if not defined ANUMAAN_ENGINE_ID set "ANUMAAN_ENGINE_ID=rotax_915is"
    if errorlevel 2 if not defined ANUMAAN_ENGINE_ID set "ANUMAAN_ENGINE_ID=rotax_914"
    if errorlevel 1 if not defined ANUMAAN_ENGINE_ID set "ANUMAAN_ENGINE_ID=rotax_912is"
)

rem 3. Resolve target 3D blend model (Unified master twin asset containing all engines)
set "TARGET_BLEND=%~dp0assets\blender\anumaan_master_twin.blend"
if not exist "%TARGET_BLEND%" set "TARGET_BLEND=%~dp0assets\blender\rotax_912_is_sport.blend"

echo.
echo [ACTIVE TWIN] Initial Engine: %ANUMAAN_ENGINE_ID%
echo [3D ASSET]    Master Model:   %TARGET_BLEND%
echo.

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

echo [1/2] Checking Backend Server link on port 8000...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 1 -UseBasicParsing | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Backend server offline - starting in Autonomous Digital Twin Mode.
) else (
    echo [OK] Backend server connected (20 Hz live telemetry active).
)

echo [2/2] Launching 3D Digital Twin Client (EEVEE Viewport Mode)...
echo.

"%BLENDER_EXE%" "%TARGET_BLEND%" --python "%~dp0apps\blender_twin\standalone_digital_twin_app.py"

@echo off
chcp 65001 >nul
title DRDO ANUMAAN // 3D Aerospace Engine Technical Showcase Launcher
color 0B
cls
echo ==============================================================================
echo        DRDO ANUMAAN DIGITAL TWIN // 3D TECHNICAL SHOWCASE & INSPECTOR
echo        DRDO / iDEX Problem Statement ID: 26054
echo ==============================================================================
echo.
echo Select an engine showcase to launch in Blender:
echo.
echo   [1] Rotax 912 iS Sport Fuel-Injected Aero Engine (100 HP)
echo   [2] Rotax 914 F Turbocharged Aero Engine (115 HP)
echo   [3] Rotax 915 iS Turbocharged Intercooled Aero Engine (141 HP)
echo   [4] Austro Engine AE300 / AE330 Common-Rail Turbodiesel (180 HP)
echo   [5] DRDO VRDE / Jayem 2.2L Indigenous TAPAS UAV Turbodiesel (180 HP)
echo.
echo   [6] Open Master Showcase (Interactive Engine Switcher)
echo   [7] Open Offline Renders Directory in Windows Explorer
echo   [0] Exit
echo.
set /p choice="Enter selection [0-7]: "

if "%choice%"=="1" call "%~dp0launch_rotax_912is_showcase.bat" & goto end
if "%choice%"=="2" call "%~dp0launch_rotax_914_showcase.bat" & goto end
if "%choice%"=="3" call "%~dp0launch_rotax_915is_showcase.bat" & goto end
if "%choice%"=="4" call "%~dp0launch_austro_ae300_showcase.bat" & goto end
if "%choice%"=="5" call "%~dp0launch_vrde_jayem_2_2l_showcase.bat" & goto end
if "%choice%"=="6" call "%~dp0launch_standalone_app.bat" & goto end
if "%choice%"=="7" explorer.exe "%~dp0assets\renders\engines" & goto end

:end

@echo off
setlocal enabledelayedexpansion
title ROTAX DIGITAL TWIN - GLOBAL PUBLIC INTERNET TUNNEL (4G/5G CELLULAR ACCESS)

echo ===============================================================================
echo   ROTAX 912 iS DIGITAL TWIN - GLOBAL INTERNET TUNNEL (OUTSIDE WI-FI ACCESS)
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.

cd /d "%~dp0"

echo This tool allows your Mobile Phone to control the Blender 3D Engine from
echo ANYWHERE IN THE WORLD over 4G/5G cellular data without being on the same Wi-Fi!
echo.
echo -------------------------------------------------------------------------------
echo Step 1: Starting Global Secure HTTPS Tunnel for Laptop Port 8000...
echo.

if exist "tools\ngrok.exe" (
    echo [OK] Launching ngrok global tunnel...
    tools\ngrok.exe http 8000 --url https://font-unmindful-manhood.ngrok-free.dev
) else (
    echo [OK] Launching npx ngrok...
    npx -y ngrok http 8000 --url https://font-unmindful-manhood.ngrok-free.dev
)

pause

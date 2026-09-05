@echo off
title ROTAX DIGITAL TWIN - WEB DASHBOARD (MOBILE GCS)
cd /d "%~dp0frontend"

echo ===============================================================================
echo ROTAX 912 iS SPORT - MOBILE COCKPIT / WEB DASHBOARD
echo DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.
if not exist "node_modules" (
    echo [!] node_modules not found - running npm install first...
    call npm install
)

echo [INFO] Building production bundle and serving it on host 0.0.0.0:5173...
echo [INFO] A live-fire demo is more reliable served this way than via "npm run dev":
echo [INFO] no dev-mode HMR websocket to drop/reconnect and no unminified dev overlay
echo [INFO] getting in the way if a component throws. Watch for the "Network:" line(s)
echo [INFO] below once it's up - use whichever one matches the network your phone is on.
echo.
echo -------------------------------------------------------------------------------
call npm run build
if errorlevel 1 (
    echo [ERROR] Build failed - see above. Falling back to the dev server instead.
    npm run dev
) else (
    call npm run preview -- --host 0.0.0.0 --port 5173
)
pause

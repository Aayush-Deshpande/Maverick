@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: -----------------------------------------------------------------------------
:: PROJECT ANUMAAN // DRDO / iDEX Problem Statement ID: 26054
:: Aero-Piston Multi-Engine 3D Digital Twin Visualizer (Three.js WebGL Client)
:: -----------------------------------------------------------------------------

:: 1. Preserve original environment state for clean restoration on exit
for /f "tokens=2 delims=:" %%a in ('chcp') do set "_ORIG_CHCP=%%a"
set "_ORIG_CHCP=%_ORIG_CHCP: =%"
if not "%_ORIG_CHCP%"=="" chcp 65001 >nul 2>&1
title ANUMAAN // Aero-Piston 3D Digital Twin Showcase
color 0B
set "PYTHONUTF8=1"

:: 2. Base paths and configuration defaults
set "ROOT=%~dp0"
set "DEFAULT_PORT=8791"
set "PORT=%DEFAULT_PORT%"
set "ENGINE="
set "WINDOW_SIZE=1600,900"
set "BROWSER_REQ=auto"
set "MODE_KIOSK=0"
set "MODE_MAX=0"
set "CLEAN_PROFILE=0"
set "SERVER_ONLY=0"
set "NO_SERVER=0"
set "VERBOSE=0"
set "TIMEOUT_SEC=15"

:: Visual & Graphics Fidelity Defaults
set "QUALITY=ultra"
set "DPR_ARG="
set "SHADOWS_ARG="
set "EXPOSURE_ARG="
set "MSAA_SAMPLES=8"
set "GPU_MEM_MB=4096"
set "ANGLE_BACKEND=d3d11"
set "UNCAPPED_FPS=0"
set "FORCE_DGPU=1"

:: 3. Command Line Argument Parser
:parse_args
if "%~1"=="" goto :args_done

:: Help & Diagnostics
if /i "%~1"=="-h" goto :show_help
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="/?" goto :show_help
if /i "%~1"=="help" goto :show_help

:: Server Lifecycle Management
if /i "%~1"=="--stop" goto :stop_server
if /i "%~1"=="-k" goto :stop_server
if /i "%~1"=="--kill" goto :stop_server
if /i "%~1"=="stop" goto :stop_server
if /i "%~1"=="kill" goto :stop_server

if /i "%~1"=="--status" goto :check_status
if /i "%~1"=="-s" goto :check_status
if /i "%~1"=="status" goto :check_status

if /i "%~1"=="--restart" goto :do_restart
if /i "%~1"=="-r" goto :do_restart
if /i "%~1"=="restart" goto :do_restart

:: Port and Engine Configuration
if /i "%~1"=="--port" (
    set "PORT=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-p" (
    set "PORT=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--engine" (
    set "ENGINE=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-e" (
    set "ENGINE=%~2"
    shift
    shift
    goto :parse_args
)

:: Browser and Display Configuration
if /i "%~1"=="--browser" (
    set "BROWSER_REQ=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-b" (
    set "BROWSER_REQ=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--window-size" (
    set "WINDOW_SIZE=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--kiosk" (
    set "MODE_KIOSK=1"
    shift
    goto :parse_args
)

if /i "%~1"=="--fullscreen" (
    set "MODE_MAX=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--maximized" (
    set "MODE_MAX=1"
    shift
    goto :parse_args
)

if /i "%~1"=="--reset-profile" (
    set "CLEAN_PROFILE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--clean" (
    set "CLEAN_PROFILE=1"
    shift
    goto :parse_args
)

:: Execution Modes
if /i "%~1"=="--server-only" (
    set "SERVER_ONLY=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--no-browser" (
    set "SERVER_ONLY=1"
    shift
    goto :parse_args
)

if /i "%~1"=="--no-server" (
    set "NO_SERVER=1"
    shift
    goto :parse_args
)

if /i "%~1"=="--verbose" (
    set "VERBOSE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--debug" (
    set "VERBOSE=1"
    shift
    goto :parse_args
)
if /i "%~1"=="-v" (
    set "VERBOSE=1"
    shift
    goto :parse_args
)

if /i "%~1"=="--timeout" (
    set "TIMEOUT_SEC=%~2"
    shift
    shift
    goto :parse_args
)

:: Visual Quality and Graphical Fidelity Options
if /i "%~1"=="--quality" (
    set "QUALITY=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="-q" (
    set "QUALITY=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--dpr" (
    set "DPR_ARG=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--shadows" (
    set "SHADOWS_ARG=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--exposure" (
    set "EXPOSURE_ARG=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--msaa" (
    set "MSAA_SAMPLES=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--gpu-mem" (
    set "GPU_MEM_MB=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--angle" (
    set "ANGLE_BACKEND=%~2"
    shift
    shift
    goto :parse_args
)

if /i "%~1"=="--uncapped-fps" (
    set "UNCAPPED_FPS=1"
    shift
    goto :parse_args
)

if /i "%~1"=="--force-dgpu" (
    set "FORCE_DGPU=1"
    shift
    goto :parse_args
)

if /i "%~1"=="--no-dgpu" (
    set "FORCE_DGPU=0"
    shift
    goto :parse_args
)

:: Shorthand Engine Identifiers
if /i "%~1"=="1" ( set "ENGINE=rotax_912is" & shift & goto :parse_args )
if /i "%~1"=="912" ( set "ENGINE=rotax_912is" & shift & goto :parse_args )
if /i "%~1"=="rotax_912is" ( set "ENGINE=rotax_912is" & shift & goto :parse_args )
if /i "%~1"=="2" ( set "ENGINE=rotax_914" & shift & goto :parse_args )
if /i "%~1"=="914" ( set "ENGINE=rotax_914" & shift & goto :parse_args )
if /i "%~1"=="rotax_914" ( set "ENGINE=rotax_914" & shift & goto :parse_args )
if /i "%~1"=="3" ( set "ENGINE=rotax_915is" & shift & goto :parse_args )
if /i "%~1"=="915" ( set "ENGINE=rotax_915is" & shift & goto :parse_args )
if /i "%~1"=="rotax_915is" ( set "ENGINE=rotax_915is" & shift & goto :parse_args )

:: Fallback positional argument: assign to ENGINE if not set
if not defined ENGINE (
    set "ENGINE=%~1"
    shift
    goto :parse_args
)

shift
goto :parse_args

:args_done

:: -----------------------------------------------------------------------------
:: GRAPHICS PRESET CALIBRATION & HARDWARE ACCELERATION
:: -----------------------------------------------------------------------------
set "TARGET_DPR=%DPR_ARG%"
set "TARGET_SHADOWS=%SHADOWS_ARG%"
set "TARGET_EXPOSURE=%EXPOSURE_ARG%"

if /i "%QUALITY%"=="ultra" (
    if not defined TARGET_DPR set "TARGET_DPR=2.5"
    if not defined TARGET_SHADOWS set "TARGET_SHADOWS=4096"
    if not defined TARGET_EXPOSURE set "TARGET_EXPOSURE=1.28"
    if not defined MSAA_SAMPLES set "MSAA_SAMPLES=8"
    if not defined GPU_MEM_MB set "GPU_MEM_MB=4096"
) else if /i "%QUALITY%"=="high" (
    if not defined TARGET_DPR set "TARGET_DPR=2.0"
    if not defined TARGET_SHADOWS set "TARGET_SHADOWS=2048"
    if not defined TARGET_EXPOSURE set "TARGET_EXPOSURE=1.25"
    if not defined MSAA_SAMPLES set "MSAA_SAMPLES=4"
    if not defined GPU_MEM_MB set "GPU_MEM_MB=2048"
) else if /i "%QUALITY%"=="perf" (
    set "QUALITY=perf"
    if not defined TARGET_DPR set "TARGET_DPR=1.0"
    if not defined TARGET_SHADOWS set "TARGET_SHADOWS=off"
    if not defined TARGET_EXPOSURE set "TARGET_EXPOSURE=1.15"
    if not defined MSAA_SAMPLES set "MSAA_SAMPLES=2"
    if not defined GPU_MEM_MB set "GPU_MEM_MB=1024"
) else (
    set "QUALITY=ultra"
    if not defined TARGET_DPR set "TARGET_DPR=2.5"
    if not defined TARGET_SHADOWS set "TARGET_SHADOWS=4096"
    if not defined TARGET_EXPOSURE set "TARGET_EXPOSURE=1.28"
)

:: Enforce discrete high-performance GPU shims (NVIDIA / AMD) on hybrid dual-GPU systems
if "!FORCE_DGPU!"=="1" (
    set "SHIM_MCCOMPAT=0x00000001"
    set "__NV_PRIME_RENDER_OFFLOAD=1"
    set "__GLX_VENDOR_LIBRARY_NAME=nvidia"
    set "DRI_PRIME=1"
)

:: -----------------------------------------------------------------------------
:: BANNER DISPLAY
:: -----------------------------------------------------------------------------
echo ===============================================================================
echo   PROJECT ANUMAAN ^|^| 3D TECHNICAL SHOWCASE ^| THREE.JS STANDALONE
echo   DRDO / iDEX Problem Statement ID: 26054
echo ===============================================================================
echo.

:: -----------------------------------------------------------------------------
:: INTERACTIVE ENGINE SELECTION (if not specified via CLI)
:: -----------------------------------------------------------------------------
if "%ENGINE%"=="" (
    if "!SERVER_ONLY!"=="1" (
        set "ENGINE=rotax_912is"
    ) else (
        echo   Select Initial Engine Digital Twin to visualize:
        echo     [1] Rotax 912 iS Sport   [100 hp Naturally Aspirated EFI  - Baseline]
        echo     [2] Rotax 914 F Turbo    [115 hp Turbocharged TCU         - High-Alt Boost]
        echo     [3] Rotax 915 iS Turbo   [141 hp Intercooled Dual FADEC   - Heavy-Lift]
        echo.
        echo     [CONTROLS]
        echo       [F1-F3] Switch Engine    [1-4] Inject Fault
        echo       [5] Clear Fault         [0/ESC] Full Assembly
        echo       [X] Exploded View       [T] Thermal Heatmap
        echo       [W] Wireframe Mode       [F] Fault Injection  [M] Audio Synthesizer
        echo.
        choice /c 123 /t 4 /d 1 /m "  Select engine [1-3] [Auto-selects 1 in 4s]: "
        if errorlevel 3 if not defined ENGINE set "ENGINE=rotax_915is"
        if errorlevel 2 if not defined ENGINE set "ENGINE=rotax_914"
        if errorlevel 1 if not defined ENGINE set "ENGINE=rotax_912is"
        echo.
    )
)

:: Validate engine selection
if not "%ENGINE%"=="rotax_912is" if not "%ENGINE%"=="rotax_914" if not "%ENGINE%"=="rotax_915is" (
    echo   [WARN] Unknown engine '%ENGINE%'. Falling back to default 'rotax_912is'.
    set "ENGINE=rotax_912is"
)

echo   [ACTIVE TWIN] Engine:  %ENGINE%
echo   [GRAPHICS]    Quality: %QUALITY% ^| DPR: !TARGET_DPR! ^| Shadows: !TARGET_SHADOWS! ^| MSAA: !MSAA_SAMPLES!x ^| VRAM: !GPU_MEM_MB!MB
echo   [PIPELINE]    ANGLE Backend: Direct3D 11 (!ANGLE_BACKEND!) ^| Color Space: sRGB Filmic
for /f "tokens=*" %%g in ('powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name" 2^>nul') do (
    echo   [GPU HARDWARE] %%g
)

:: -----------------------------------------------------------------------------
:: PRE-FLIGHT ASSET INTEGRITY CHECKS
:: -----------------------------------------------------------------------------
if not exist "%ROOT%apps\threejs_twin\index.html" (
    echo   [FATAL ERROR] Web application index file not found at:
    echo                 %ROOT%apps\threejs_twin\index.html
    echo   Please verify your workspace repository integrity.
    pause
    goto :cleanup_and_exit
)

set "ACTIVE_GLB=%ROOT%apps\threejs_twin\assets\models\draco\%ENGINE%.glb"
if exist "%ACTIVE_GLB%" (
    for %%F in ("%ACTIVE_GLB%") do set "_GLB_SIZE=%%~zF"
    if !_GLB_SIZE! LSS 2048 (
        echo   [WARNING] Model file %ENGINE%.glb is only !_GLB_SIZE! bytes.
        echo             It appears to be an unpulled Git LFS pointer stub.
        echo             Run "git lfs pull" if 3D geometry fails to display.
    )
) else (
    echo   [WARNING] 3D Draco model not found: %ACTIVE_GLB%
)

:: Check Backend Telemetry Server on Port 8000
set "BACKEND_ONLINE=0"
where curl >nul 2>nul
if not errorlevel 1 (
    for /f "tokens=*" %%h in ('curl -s -o nul -w "%%{http_code}" --connect-timeout 1 "http://127.0.0.1:8000/api/health" 2^>nul') do (
        if "%%h"=="200" set "BACKEND_ONLINE=1"
    )
) else (
    powershell -NoProfile -Command "try { if ((Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 1 -UseBasicParsing).StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 set "BACKEND_ONLINE=1"
)

if "!BACKEND_ONLINE!"=="1" (
    echo   [BACKEND]     Telemetry Bridge: CONNECTED [20 Hz Real-Time DRDO Link]
) else (
    echo   [BACKEND]     Telemetry Bridge: OFFLINE [Operating in Autonomous Mode]
)
echo.

:: -----------------------------------------------------------------------------
:: PORT VERIFICATION & DYNAMIC FAILOVER
:: -----------------------------------------------------------------------------
set "PID_FILE=%TEMP%\anumaan_threejs_server_%PORT%.pid"
set "LOG_FILE=%TEMP%\anumaan_threejs_server.log"
set "REUSE_SERVER=0"

:: Check if our own server is already responding on this port
where curl >nul 2>nul
if not errorlevel 1 (
    for /f "tokens=*" %%h in ('curl -s -o nul -w "%%{http_code}" --connect-timeout 1 "http://127.0.0.1:%PORT%/apps/threejs_twin/index.html" 2^>nul') do (
        if "%%h"=="200" set "REUSE_SERVER=1"
    )
) else (
    powershell -NoProfile -Command "try { if ((Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT%/apps/threejs_twin/index.html' -TimeoutSec 1 -UseBasicParsing).StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 set "REUSE_SERVER=1"
)

:: If not our server, check if port is occupied by an external process
if "!REUSE_SERVER!"=="0" (
    set "_OCCUPIED_PID="
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do set "_OCCUPIED_PID=%%p"
    if defined _OCCUPIED_PID (
        echo   [WARN] Port %PORT% occupied by external process [PID: !_OCCUPIED_PID!].
        echo          Attempting automatic port failover...
        set "FOUND_ALT="
        for %%P in (8792 8793 8794 8795 8796 8797 8798 8799) do (
            if not defined FOUND_ALT (
                set "_P_OCC="
                for /f "tokens=5" %%x in ('netstat -ano ^| findstr ":%%P" ^| findstr "LISTENING"') do set "_P_OCC=%%x"
                if not defined _P_OCC (
                    set "PORT=%%P"
                    set "FOUND_ALT=1"
                    echo   [INFO] Automatically switched to open port !PORT!.
                )
            )
        )
        if not defined FOUND_ALT (
            echo   [ERROR] No open ports available in range 8791-8799. Aborting.
            pause
            goto :cleanup_and_exit
        )
        set "PID_FILE=%TEMP%\anumaan_threejs_server_!PORT!.pid"
    )
)

set "APP_URL=http://127.0.0.1:%PORT%/apps/threejs_twin/index.html?engine=%ENGINE%&quality=%QUALITY%&dpr=!TARGET_DPR!&shadows=!TARGET_SHADOWS!&exposure=!TARGET_EXPOSURE!"

:: -----------------------------------------------------------------------------
:: LOCAL ASSET SERVER LIFECYCLE MANAGEMENT
:: -----------------------------------------------------------------------------
if "!REUSE_SERVER!"=="1" (
    echo   [1/2] Local static asset server is already running on port %PORT% [OK]
) else if "!NO_SERVER!"=="1" (
    echo   [1/2] Server start skipped [--no-server requested].
) else (
    echo   [1/2] Starting local static asset server on port %PORT%...
    
    :: Identify best PowerShell executable
    set "PS_BIN="
    where pwsh >nul 2>nul && set "PS_BIN=pwsh"
    if not defined PS_BIN set "PS_BIN=powershell"
    
    set "WIN_STYLE=Hidden"
    if "!VERBOSE!"=="1" set "WIN_STYLE=Normal"

    if exist "%ROOT%scripts\tools\serve_static.ps1" (
        start "AnumaanTwinServer_%PORT%" /min !PS_BIN! -NoProfile -WindowStyle !WIN_STYLE! -ExecutionPolicy Bypass -File "%ROOT%scripts\tools\serve_static.ps1" -Root "%ROOT%." -Port %PORT%
    ) else (
        echo   [INFO] serve_static.ps1 not found. Falling back to Python http.server...
        start "AnumaanTwinServer_%PORT%" /min python -m http.server %PORT% --directory "%ROOT%."
    )

    :: Polling readiness loop with high-speed curl and visual indicator
    <nul set /p "=        Awaiting server readiness "
    set "SERVER_READY="
    set /a "MAX_CYCLES=%TIMEOUT_SEC% * 2"
    
    for /l %%i in (1,1,!MAX_CYCLES!) do (
        if not defined SERVER_READY (
            where curl >nul 2>nul
            if not errorlevel 1 (
                for /f "tokens=*" %%c in ('curl -s -o nul -w "%%{http_code}" --connect-timeout 1 "http://127.0.0.1:%PORT%/apps/threejs_twin/index.html" 2^>nul') do (
                    if "%%c"=="200" set "SERVER_READY=1"
                )
            ) else (
                powershell -NoProfile -Command "try { if ((Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT%/apps/threejs_twin/index.html' -TimeoutSec 1 -UseBasicParsing).StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
                if not errorlevel 1 set "SERVER_READY=1"
            )
            
            if defined SERVER_READY (
                echo  [OK]
            ) else (
                <nul set /p "=."
                timeout /t 1 /nobreak >nul 2>&1 || ping -n 2 127.0.0.1 >nul
            )
        )
    )

    if not defined SERVER_READY goto :server_timeout_fail
)

if "!SERVER_ONLY!"=="1" goto :server_only_exit

:: -----------------------------------------------------------------------------
:: BROWSER DETECTION & ISOLATED PROFILE PROVISIONING
:: -----------------------------------------------------------------------------
echo   [2/2] Launching 3D Digital Twin visualization client...

set "CHROME_BIN="
set "EDGE_BIN="
set "BRAVE_BIN="

:: 1. Registry Query (Standard Windows App Paths)
for /f "tokens=2*" %%a in ('reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve 2^>nul') do set "CHROME_BIN=%%b"
if not defined CHROME_BIN for /f "tokens=2*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" /ve 2^>nul') do set "CHROME_BIN=%%b"

for /f "tokens=2*" %%a in ('reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe" /ve 2^>nul') do set "EDGE_BIN=%%b"
if not defined EDGE_BIN for /f "tokens=2*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe" /ve 2^>nul') do set "EDGE_BIN=%%b"

for /f "tokens=2*" %%a in ('reg query "HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths\brave.exe" /ve 2^>nul') do set "BRAVE_BIN=%%b"
if not defined BRAVE_BIN for /f "tokens=2*" %%a in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\brave.exe" /ve 2^>nul') do set "BRAVE_BIN=%%b"

:: 2. Standard Program Files and Per-User AppData Paths
if not defined CHROME_BIN if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME_BIN=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_BIN if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME_BIN=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_BIN if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "CHROME_BIN=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if not defined EDGE_BIN if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "EDGE_BIN=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined EDGE_BIN if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE_BIN=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined EDGE_BIN if exist "%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe" set "EDGE_BIN=%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"

if not defined BRAVE_BIN if exist "%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BRAVE_BIN=%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"
if not defined BRAVE_BIN if exist "%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BRAVE_BIN=%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe"
if not defined BRAVE_BIN if exist "%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe" set "BRAVE_BIN=%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"

:: 3. PATH Search via where.exe
if not defined CHROME_BIN (
    for /f "tokens=*" %%i in ('where chrome.exe 2^>nul') do if not defined CHROME_BIN set "CHROME_BIN=%%i"
)
if not defined EDGE_BIN (
    for /f "tokens=*" %%i in ('where msedge.exe 2^>nul') do if not defined EDGE_BIN set "EDGE_BIN=%%i"
)
if not defined BRAVE_BIN (
    for /f "tokens=*" %%i in ('where brave.exe 2^>nul') do if not defined BRAVE_BIN set "BRAVE_BIN=%%i"
)

:: Select target browser executable based on preference
set "TARGET_BROWSER="
set "BROWSER_NAME="
set "PROFILE_SUBDIR="

if /i "%BROWSER_REQ%"=="chrome" if defined CHROME_BIN (
    set "TARGET_BROWSER=%CHROME_BIN%"
    set "BROWSER_NAME=Google Chrome"
    set "PROFILE_SUBDIR=ChromeProfile"
)
if /i "%BROWSER_REQ%"=="edge" if defined EDGE_BIN (
    set "TARGET_BROWSER=%EDGE_BIN%"
    set "BROWSER_NAME=Microsoft Edge"
    set "PROFILE_SUBDIR=EdgeProfile"
)
if /i "%BROWSER_REQ%"=="brave" if defined BRAVE_BIN (
    set "TARGET_BROWSER=%BRAVE_BIN%"
    set "BROWSER_NAME=Brave Browser"
    set "PROFILE_SUBDIR=BraveProfile"
)

:: Auto-detection priority: Chrome -> Edge -> Brave
if not defined TARGET_BROWSER if defined CHROME_BIN (
    set "TARGET_BROWSER=%CHROME_BIN%"
    set "BROWSER_NAME=Google Chrome"
    set "PROFILE_SUBDIR=ChromeProfile"
)
if not defined TARGET_BROWSER if defined EDGE_BIN (
    set "TARGET_BROWSER=%EDGE_BIN%"
    set "BROWSER_NAME=Microsoft Edge"
    set "PROFILE_SUBDIR=EdgeProfile"
)
if not defined TARGET_BROWSER if defined BRAVE_BIN (
    set "TARGET_BROWSER=%BRAVE_BIN%"
    set "BROWSER_NAME=Brave Browser"
    set "PROFILE_SUBDIR=BraveProfile"
)

:: Browser Execution & Chromium Hardware Acceleration Flags
set "GPU_FLAGS=--enable-gpu-rasterization --ignore-gpu-blocklist --enable-zero-copy --use-angle=!ANGLE_BACKEND! --canvas-msaa-sample-count=!MSAA_SAMPLES! --force-gpu-mem-available-mb=!GPU_MEM_MB! --force-color-profile=srgb --enable-webgl-draft-extensions --enable-accelerated-2d-canvas --disable-backgrounding-occluded-windows --disable-renderer-backgrounding"

if "!UNCAPPED_FPS!"=="1" (
    set "GPU_FLAGS=!GPU_FLAGS! --disable-frame-rate-limit --disable-gpu-vsync"
)

set "BROWSER_FLAGS=--app="!APP_URL!" --new-window --no-first-run --no-default-browser-check --disable-translate --disable-extensions --autoplay-policy=no-user-gesture-required !GPU_FLAGS!"

if "%MODE_KIOSK%"=="1" (
    set "BROWSER_FLAGS=!BROWSER_FLAGS! --kiosk"
) else if "%MODE_MAX%"=="1" (
    set "BROWSER_FLAGS=!BROWSER_FLAGS! --start-maximized"
) else (
    set "BROWSER_FLAGS=!BROWSER_FLAGS! --window-size=%WINDOW_SIZE%"
)

if defined TARGET_BROWSER (
    set "PROFILE_DIR=%LOCALAPPDATA%\AnumaanTwinApp\%PROFILE_SUBDIR%"
    if "!CLEAN_PROFILE!"=="1" (
        if exist "!PROFILE_DIR!" (
            echo   [INFO] Resetting isolated browser profile cache...
            rmdir /s /q "!PROFILE_DIR!" >nul 2>&1
        )
    )
    if not exist "!PROFILE_DIR!" mkdir "!PROFILE_DIR!" >nul 2>&1

    :: Remove stale Chromium SingletonLock to avoid hung window instances
    if exist "!PROFILE_DIR!\SingletonLock" del /f /q "!PROFILE_DIR!\SingletonLock" >nul 2>&1

    echo   [CLIENT]      Browser: %BROWSER_NAME% [App Mode]
    echo   [CLIENT]      Profile: !PROFILE_DIR!
    start "" "%TARGET_BROWSER%" !BROWSER_FLAGS! --user-data-dir="!PROFILE_DIR!"
) else (
    echo   [CLIENT]      Browser: System Default [App Mode unavailable]
    start "" "!APP_URL!"
)

echo.
echo ===============================================================================
echo   PROJECT ANUMAAN // DIGITAL TWIN ACTIVE
echo   Showcase URL: !APP_URL!
echo   Interactive Controls:
echo     [F1-F3] Switch Engine:
echo             [F1] Rotax 912 iS  ^|  [F2] Rotax 914 F    ^|  [F3] Rotax 915 iS
echo     [1-4]   Inject Engine Fault           [5] Clear Fault
echo     [0/ESC] Full Assembly View
echo     [X]     Exploded Assembly View       [T]     Thermal Heatmap Mode
echo     [W]     CAD Wireframe Overlay        [F]     Fault Injection Rig
echo     [M]     Acoustic Engine Audio        [P]     Capture 4K Snapshot
echo.
echo   Management:
echo     Run "launch_threejs_twin.bat --stop" to terminate the static asset server.
echo     Run "launch_threejs_twin.bat --status" to view runtime health and port.
echo ===============================================================================
echo.
goto :cleanup_and_exit

:: -----------------------------------------------------------------------------
:: SUBROUTINE: SERVER TIMEOUT / ONLY EXITS
:: -----------------------------------------------------------------------------
:server_timeout_fail
echo.
echo   [ERROR] Local static server failed to answer on port %PORT% within %TIMEOUT_SEC%s.
if exist "%LOG_FILE%" (
    echo   Last server log entries:
    powershell -NoProfile -Command "Get-Content -Path '%LOG_FILE%' -Tail 10" 2>nul
)
pause
goto :cleanup_and_exit

:server_only_exit
echo.
echo   [OK] Server running at: http://127.0.0.1:%PORT%/
echo   [INFO] Headless server-only mode active.
echo   Run "launch_threejs_twin.bat --stop" to terminate server.
goto :cleanup_and_exit

:: -----------------------------------------------------------------------------
:: SUBROUTINE: STOP SERVER
:: -----------------------------------------------------------------------------
:stop_server
echo ===============================================================================
echo   PROJECT ANUMAAN // TERMINATING 3D TWIN ASSET SERVER
echo ===============================================================================
set "_KILLED=0"

:: 1. Terminate via saved PID lockfile if present
set "PID_FILE=%TEMP%\anumaan_threejs_server_%PORT%.pid"
if exist "%PID_FILE%" (
    set /p _SAVED_PID=<"%PID_FILE%"
    if defined _SAVED_PID (
        taskkill /F /PID !_SAVED_PID! >nul 2>&1
        set "_KILLED=1"
    )
    del /f /q "%PID_FILE%" >nul 2>&1
)

:: 2. Terminate PowerShell instances running serve_static.ps1 for this port
powershell -NoProfile -Command "$procs = Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%%serve_static.ps1%%' AND CommandLine LIKE '%%%PORT%%%'\" -ErrorAction SilentlyContinue; if ($procs) { $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 set "_KILLED=1"

:: 3. Terminate via netstat PID (if not system PID 4 or 0)
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    if not "%%p"=="4" if not "%%p"=="0" (
        echo   [INFO] Terminating socket owner PID %%p...
        taskkill /F /PID %%p >nul 2>&1
        set "_KILLED=1"
    )
)

if "!_KILLED!"=="1" (
    echo   [OK] Asset server on port %PORT% has been stopped.
) else (
    echo   [INFO] No active asset server found on port %PORT%.
)
goto :cleanup_and_exit

:: -----------------------------------------------------------------------------
:: SUBROUTINE: CHECK STATUS
:: -----------------------------------------------------------------------------
:check_status
echo ===============================================================================
echo   PROJECT ANUMAAN // 3D DIGITAL TWIN STATUS REPORT
echo ===============================================================================
echo   Port: %PORT%

set "_STATUS_ONLINE=0"
set "_FOUND_PID="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    set "_FOUND_PID=%%p"
    set "_STATUS_ONLINE=1"
)

if "!_STATUS_ONLINE!"=="1" (
    echo   Status: ONLINE [Port Listener PID: !_FOUND_PID!]
) else (
    echo   Status: OFFLINE [Not listening on port %PORT%]
)

set "PID_FILE=%TEMP%\anumaan_threejs_server_%PORT%.pid"
if exist "%PID_FILE%" (
    set /p _PID_VAL=<"%PID_FILE%"
    if defined _PID_VAL (
        tasklist /FI "PID eq !_PID_VAL!" 2>nul | findstr /i "!_PID_VAL!" >nul
        if not errorlevel 1 (
            echo   Server Process PID: !_PID_VAL! [Active]
        ) else (
            echo   Server Process PID: !_PID_VAL! [Stale Lockfile / Process Ended]
            del /f /q "%PID_FILE%" >nul 2>&1
        )
    )
)

if "!_STATUS_ONLINE!"=="1" (
    powershell -NoProfile -Command "try { $s = (Invoke-WebRequest -Uri 'http://127.0.0.1:%PORT%/apps/threejs_twin/index.html' -TimeoutSec 2 -UseBasicParsing).StatusCode; Write-Host \"  HTTP Probe: $s [Operational]\" } catch { Write-Host '  HTTP Probe: Error connecting' }"
)
goto :cleanup_and_exit

:: -----------------------------------------------------------------------------
:: SUBROUTINE: RESTART
:: -----------------------------------------------------------------------------
:do_restart
echo   [INFO] Restarting asset server on port %PORT%...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%%serve_static.ps1%%' AND CommandLine LIKE '%%%PORT%%%'\" -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
    if not "%%p"=="4" if not "%%p"=="0" taskkill /F /PID %%p >nul 2>&1
)
set "PID_FILE=%TEMP%\anumaan_threejs_server_%PORT%.pid"
if exist "%PID_FILE%" del /f /q "%PID_FILE%" >nul 2>&1
timeout /t 1 /nobreak >nul 2>&1 || ping -n 2 127.0.0.1 >nul
goto :args_done

:: -----------------------------------------------------------------------------
:: SUBROUTINE: HELP MANUAL
:: -----------------------------------------------------------------------------
:show_help
echo ===============================================================================
echo   PROJECT ANUMAAN // 3D DIGITAL TWIN SHOWCASE LAUNCHER (DRDO PS-26054)
echo ===============================================================================
echo   Usage: launch_threejs_twin.bat [OPTIONS] [ENGINE]
echo.
echo   ENGINES:
echo     1, 912, rotax_912is   Rotax 912 iS Sport   [100 hp Naturally Aspirated EFI]
echo     2, 914, rotax_914     Rotax 914 F Turbo    [115 hp TCU Turbocharger]
echo     3, 915, rotax_915is   Rotax 915 iS Turbo   [141 hp Intercooled Dual FADEC]
echo.
echo   SERVER COMMANDS:
echo     --stop, -k            Terminate the running static asset server
echo     --status, -s          Check server status, port listener, and PID
echo     --restart, -r         Restart the static asset server
echo     --port, -p ^<PORT^>     Specify custom server port (Default: 8791)
echo     --server-only         Start asset server only without launching browser
echo     --no-server           Launch browser without starting a server
echo     --timeout ^<SEC^>       Server readiness timeout in seconds (Default: 15)
echo.
echo   DISPLAY ^& BROWSER OPTIONS:
echo     --browser, -b ^<NAME^>  Force browser: chrome ^| edge ^| brave ^| default
echo     --kiosk               Launch in borderless presentation kiosk mode
echo     --fullscreen          Launch with window maximized
echo     --window-size ^<W,H^>   Set custom window dimensions (Default: 1600,900)
echo     --reset-profile       Wipe cached isolated browser profile data
echo     --verbose, -v         Enable verbose diagnostic console logging
echo     --help, -h, /?        Display this manual
echo.
echo   GRAPHICS ^& VISUAL QUALITY:
echo     --quality, -q ^<ultra^|high^|perf^>  Visual fidelity preset (Default: ultra)
echo     --dpr ^<1.0-2.5^>              Canvas Device Pixel Ratio override
echo     --shadows ^<4096^|2048^|1024^|off^> Real-time PCF soft shadow resolution
echo     --exposure ^<0.5-2.0^>          ACES Filmic tone mapping exposure
echo     --msaa ^<2^|4^|8^>               Hardware MSAA antialiasing sample count
echo     --gpu-mem ^<MB^>               Dedicated GPU VRAM budget (Default: 4096)
echo     --angle ^<d3d11^|d3d9^|gl^|vulkan^> ANGLE graphics rendering backend
echo     --uncapped-fps                 Disable Chromium 60 FPS VSync cap
echo     --force-dgpu                   Enforce high-performance discrete GPU shim (Default)
echo     --no-dgpu                      Allow system/iGPU automatic graphics selection
echo.
echo   EXAMPLES:
echo     launch_threejs_twin.bat
echo     launch_threejs_twin.bat rotax_914
echo     launch_threejs_twin.bat --engine rotax_915is --quality ultra
echo     launch_threejs_twin.bat --quality high --dpr 2.0 --uncapped-fps
echo     launch_threejs_twin.bat --port 9000 --browser chrome
echo     launch_threejs_twin.bat --stop
echo ===============================================================================
goto :cleanup_and_exit

:: -----------------------------------------------------------------------------
:: CLEANUP AND EXIT ROUTINE
:: -----------------------------------------------------------------------------
:cleanup_and_exit
if defined _ORIG_CHCP chcp %_ORIG_CHCP% >nul 2>&1
endlocal
exit /b 0

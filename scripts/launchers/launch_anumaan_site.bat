@echo off
set "ROOT=%~dp0..\..\"
echo =====================================================================
echo  PROJECT ANUMAAN // DRDO SIH 26054 AERO-PISTON DIGITAL TWIN PLATFORM
echo =====================================================================
echo  Starting local web server on port 8080...
echo  Opening browser at http://localhost:8080
echo  Press Ctrl+C to terminate the server.
echo =====================================================================

rem Copy the single canonical engine models into web\site\assets\models (card P0-07)
node "%ROOT%scripts\assets\sync_web_models.mjs" web
cd /d "%ROOT%web\site"
start "" http://localhost:8080
python -m http.server 8080
pause

@echo off
echo =====================================================================
echo  PROJECT ANUMAAN // DRDO SIH 26054 AERO-PISTON DIGITAL TWIN PLATFORM
echo =====================================================================
echo  Starting local web server on port 8080...
echo  Opening browser at http://localhost:8080
echo  Press Ctrl+C to terminate the server.
echo =====================================================================

cd /d "%~dp0web\site"
start "" http://localhost:8080
python -m http.server 8080
pause

@echo off
setlocal
title ANUMAAN - launcher menu
set "L=%~dp0scripts\launchers\"

:menu
cls
echo ===============================================================================
echo   ANUMAAN (SIH PS-26054) - launcher menu
echo   All launchers live in scripts\launchers\  (see STRUCTURE.txt)
echo ===============================================================================
echo   1  Backend server (FastAPI)
echo   2  Web dashboard (React GCS)
echo   3  Backend + Blender 3D twin for one engine
echo   4  Old three.js 3D window
echo   5  Blender engine showcase menu
echo   6  Canyon flight simulation (Blender)
echo   7  Mission graph viewer (Blender)
echo   8  Static presentation site (web\site)
echo   9  Public tunnel for the backend
echo   0  Exit
echo.
set "choice="
set /p "choice=Select: "
if "%choice%"=="1" call "%L%launch_backend_server.bat" & goto menu
if "%choice%"=="2" call "%L%launch_web_dashboard.bat" & goto menu
if "%choice%"=="3" goto engine
if "%choice%"=="4" call "%L%launch_threejs_twin.bat" & goto menu
if "%choice%"=="5" call "%L%launch_engine_showcase_menu.bat" & goto menu
if "%choice%"=="6" call "%L%launch_canyon_simulation.bat" & goto menu
if "%choice%"=="7" call "%L%launch_mission_graph.bat" & goto menu
if "%choice%"=="8" call "%L%launch_anumaan_site.bat" & goto menu
if "%choice%"=="9" call "%L%launch_public_tunnel.bat" & goto menu
if "%choice%"=="0" goto end
goto menu

:engine
echo.
echo   a  Rotax 912 iS Sport     b  Rotax 914     c  Rotax 915 iS
echo   d  Austro AE300           e  VRDE / Jayem 2.2 L
set "e="
set /p "e=Engine: "
if /i "%e%"=="a" call "%L%launch_standalone_app.bat" rotax_912is
if /i "%e%"=="b" call "%L%launch_standalone_app.bat" rotax_914
if /i "%e%"=="c" call "%L%launch_standalone_app.bat" rotax_915is
if /i "%e%"=="d" call "%L%launch_standalone_app.bat" austro_ae300
if /i "%e%"=="e" call "%L%launch_standalone_app.bat" vrde_jayem_2_2l
goto menu

:end
endlocal

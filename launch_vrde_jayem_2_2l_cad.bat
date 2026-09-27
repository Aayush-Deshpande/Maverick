@echo off
title VRDE / JAYEM 2.2L CAD 3D MODEL — BLENDER VIEWPORT
color 0E

set "BLENDER_EXE="
if exist "E:\Blender\blender.exe" set "BLENDER_EXE=E:\Blender\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
if not defined BLENDER_EXE if exist "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" set "BLENDER_EXE=C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
if not defined BLENDER_EXE (
    where blender >nul 2>nul
    if not errorlevel 1 set "BLENDER_EXE=blender"
)

if not defined BLENDER_EXE (
    echo [ERROR] Blender executable not found.
    pause
    exit /b 1
)

echo [OK] Opening VRDE / Jayem 2.2L Indigenous CRDi Diesel Model in Blender...
"%BLENDER_EXE%" "%~dp0assets\blender\vrde_jayem_2_2l.blend"

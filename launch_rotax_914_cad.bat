@echo off
title Launch Rotax 914 F Turbo CAD Digital Twin
echo ========================================================
echo  Launching Rotax 914 F Turbo (Genuine CAD Model)
echo ========================================================
set "BLENDER_EXE="
if exist "D:\Blender\blender.exe" set "BLENDER_EXE=D:\Blender\blender.exe"
if not defined BLENDER_EXE if exist "E:\Blender\blender.exe" set "BLENDER_EXE=E:\Blender\blender.exe"
if not defined BLENDER_EXE (
    echo [ERROR] Blender executable not found at D:\Blender\blender.exe or E:\Blender\blender.exe
    pause
    exit /b 1
)
start "" "%BLENDER_EXE%" "assets\blender\rotax_914.blend"

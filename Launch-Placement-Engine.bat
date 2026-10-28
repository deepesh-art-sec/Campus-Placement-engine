@echo off
title Institutional Placement Engine - Local & LAN Host
cd /d "%~dp0"

if exist "dist\PlacementEngine.exe" (
    echo Starting Institutional Placement Engine...
    start "" "dist\PlacementEngine.exe"
) else (
    echo [ERROR] dist\PlacementEngine.exe not found!
    echo Please ensure the project has been compiled or run:
    echo   .venv\Scripts\python.exe scripts\exe_launcher.py
    pause
)

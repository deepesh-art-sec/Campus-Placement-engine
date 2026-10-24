@echo off
setlocal
cd /d "%~dp0"
title Campus Placement Engine (100% Offline Standalone Mode)

echo ======================================================================
echo Starting Campus Placement Engine in 100%% Offline Standalone Mode...
echo (No internet, Wi-Fi, Ethernet, or network connection required)
echo ======================================================================

set HOST=127.0.0.1
set PORT=8000
set AUTO_OPEN_BROWSER=1

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\lan_launcher.py
) else (
    python scripts\lan_launcher.py
)
pause

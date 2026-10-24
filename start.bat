@echo off
setlocal
cd /d "%~dp0"
title Institutional Placement Engine

echo ======================================================================
echo Launching Institutional Placement Eligibility & Scheduling Engine...
echo ======================================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\lan_launcher.py
) else (
    python scripts\lan_launcher.py
)
pause

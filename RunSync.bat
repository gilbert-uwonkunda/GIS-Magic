@echo off
title City of Kigali - Approval Sync
color 0A
echo.
echo =====================================
echo    CoK Inspection Hub SYNC AGENT
echo =====================================
echo.
echo  Initializing approval synchronization...
echo.

REM Set ArcGIS Python environment
set PYTHONPATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3
set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;%PATH%

REM Run with ArcGIS Python
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "%~dp0sync_approvals.py"

echo.
echo =====================================
echo  Sync Complete! Press any key to exit
echo =====================================
pause >nul
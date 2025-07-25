@echo off
title City of Kigali - Daily BPMIS Update
color 0A
echo.
echo =====================================
echo   🏢 CITY OF KIGALI BPMIS UPDATER
echo =====================================
echo.
echo 🚀 Starting daily permit synchronization...
echo 🗑️  Removing expired permits...
echo 📅 Fetching today's API data...
echo 📥 Inserting new records...
echo.

REM Set ArcGIS Python environment
set PYTHONPATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3
set PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3;%PATH%

REM Run with ArcGIS Python
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "%~dp0daily_bpmis_update.py"

echo.
echo =====================================
echo ✅ Daily Update Complete! Press any key to exit
echo =====================================
pause >nul
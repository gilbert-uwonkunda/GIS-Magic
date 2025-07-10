@echo off
setlocal enabledelayedexpansion

:: === CONFIGURATION ===
set SCRIPT_DIR=E:\Scripts\HealthGIS_Automation\scripts
set LOG_DIR=E:\Scripts\HealthGIS_Automation\logs
set PYTHON_PATH=C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe

:: Create log directory if it doesn't exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Set timestamp for logging
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD%_%HH%-%Min%-%Sec%"

echo ============================================
echo HEALTH GIS - DAILY DATA CLEANUP
echo Date: %YYYY%-%MM%-%DD%
echo Time: %HH%:%Min%:%Sec%
echo ============================================

:: Change to script directory
cd /d "%SCRIPT_DIR%"

:: === STEP 1: TRACKS LAYER CLEANUP ===
echo.
echo STEP 1: Cleaning tracks layer data...
"%PYTHON_PATH%" "tracks_deleter.py" > "%LOG_DIR%\tracks_cleanup_%timestamp%.log" 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Tracks cleanup failed
    echo Check log: %LOG_DIR%\tracks_cleanup_%timestamp%.log
    goto :error_exit
) else (
    echo Tracks cleanup completed successfully
)

:: === STEP 2: PRESENCE LAYER CLEANUP ===
echo.
echo STEP 2: Cleaning presence layer data...
"%PYTHON_PATH%" "presence_deleter.py" > "%LOG_DIR%\presence_cleanup_%timestamp%.log" 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Presence cleanup failed
    echo Check log: %LOG_DIR%\presence_cleanup_%timestamp%.log
    goto :error_exit
) else (
    echo Presence cleanup completed successfully
)

:: === SUCCESS COMPLETION ===
echo.
echo =========================================
echo HEALTH DATA CLEANUP COMPLETED SUCCESSFULLY!
echo Logs saved to: %LOG_DIR%
echo System ready for new data collection!
echo =========================================

:: Create success marker file
echo %timestamp% > "%LOG_DIR%\last_successful_cleanup.txt"

:: Log summary to main cleanup log
echo ========== CLEANUP SUMMARY ========== > "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo Date: %YYYY%-%MM%-%DD% %HH%:%Min%:%Sec% >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo Status: SUCCESS >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo Tracks Cleanup: COMPLETED >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo Presence Cleanup: COMPLETED >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo ================================== >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"

goto :end

:: === ERROR HANDLING ===
:error_exit
echo.
echo =========================================
echo HEALTH DATA CLEANUP FAILED!
echo Contact GIS Administrator
echo Check logs in: %LOG_DIR%
echo =========================================

:: Create error marker file
echo %timestamp% - CLEANUP FAILED > "%LOG_DIR%\last_error.txt"

:: Log error summary
echo ========== CLEANUP SUMMARY ========== > "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo Date: %YYYY%-%MM%-%DD% %HH%:%Min%:%Sec% >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo Status: FAILED >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo Error Details: Check individual step logs >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo Contact: GIS Administrator >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"
echo ================================== >> "%LOG_DIR%\cleanup_summary_%timestamp%.log"

exit /b 1

:end
exit /b 0
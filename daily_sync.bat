@echo off
setlocal enabledelayedexpansion

:: === CONFIGURATION ===
set SCRIPT_DIR=C:\CoK Schedule Auto\Script
set LOG_DIR=C:\CoK Schedule Auto\Logs
set PYTHON_PATH=C:\Program Files\ArcGIS\Server\framework\runtime\ArcGIS\bin\Python\envs\arcgispro-py3\python.exe
set EMAIL_ALERT=gilbertuwonkundaa@gmail.com

:: Create log directory if it doesn't exist
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Set timestamp for logging
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD%_%HH%-%Min%-%Sec%"

echo ============================================
echo CITY OF KIGALI - DAILY LAND SYNC
echo Date: %YYYY%-%MM%-%DD%
echo Time: %HH%:%Min%:%Sec%
echo ============================================

:: Change to script directory
cd /d "%SCRIPT_DIR%"

:: === STEP 1: LAIS DAILY EXTRACTION ===
echo.
echo STEP 1: Extracting today's approvals from LAIS...
"%PYTHON_PATH%" "01_lais_daily_sync.py" > "%LOG_DIR%\extraction_%timestamp%.log" 2>&1

if !errorlevel! neq 0 (
    echo ERROR: LAIS extraction failed
    echo Check log: %LOG_DIR%\extraction_%timestamp%.log
    goto :error_exit
) else (
    echo LAIS extraction completed successfully
)

:: === STEP 2: STAGING TO LIVE SYNC ===
echo.
echo STEP 2: Syncing staging data to live database...
"%PYTHON_PATH%" "02_staging_to_live_sync.py" > "%LOG_DIR%\sync_%timestamp%.log" 2>&1

if !errorlevel! neq 0 (
    echo ERROR: Staging sync failed
    echo Check log: %LOG_DIR%\sync_%timestamp%.log
    goto :error_exit
) else (
    echo Staging sync completed successfully
)

:: === STEP 3: UPDATE NULL FIELD VALUES ===
echo.
echo STEP 3: Updating NULL field values...
"%PYTHON_PATH%" "03_update_null_fields.py" > "%LOG_DIR%\null_update_%timestamp%.log" 2>&1

if !errorlevel! neq 0 (
    echo ERROR: NULL field update failed
    echo Check log: %LOG_DIR%\null_update_%timestamp%.log
    goto :error_exit
) else (
    echo NULL field update completed successfully
)

:: === SUCCESS COMPLETION ===
echo.
echo =========================================
echo DAILY SYNC COMPLETED SUCCESSFULLY!
echo Logs saved to: %LOG_DIR%
echo Ready for your workout!
echo =========================================

:: Create success marker file
echo %timestamp% > "%LOG_DIR%\last_successful_sync.txt"

goto :end

:: === ERROR HANDLING ===
:error_exit
echo.
echo =========================================
echo DAILY SYNC FAILED!
echo Contact IT Support
echo Check logs in: %LOG_DIR%
echo =========================================

:: Create error marker file
echo %timestamp% - SYNC FAILED > "%LOG_DIR%\last_error.txt"

:: Optional: Send email alert (requires configured mail client)
:: echo Daily sync failed at %timestamp% | mail -s "URGENT: Land Sync Failed" %EMAIL_ALERT%

exit /b 1

:end
exit /b 0
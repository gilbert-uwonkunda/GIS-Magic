@echo off
:: ============================================================================
:: INSPECTION HUB AUTO - BPMIS PERMIT MANAGEMENT AUTOMATION
:: ============================================================================
:: This batch file runs the complete BPMIS permit update process:
:: 1. Updates BPMIS_Current table with latest API data  
:: 2. Syncs approval status to CoK_Parcels_live_data
:: ============================================================================

:: Configuration - CONFIGURED FOR YOUR SYSTEM
set "PYTHON_EXE=C:\Program Files\ArcGIS\Server\framework\runtime\ArcGIS\bin\Python\envs\arcgispro-py3\python.exe"
set "SCRIPT_DIR=C:\CoK Schedule Auto\GeoBuildInspector"
set "LOG_DIR=C:\CoK Schedule Auto\GeoBuildInspector\Logs"

:: Create directories if they don't exist
if not exist "%SCRIPT_DIR%" mkdir "%SCRIPT_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Create timestamp for logging
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%_%dt:~8,2%-%dt:~10,2%-%dt:~12,2%"

cls
echo.
echo ============================================================================
echo                    INSPECTION HUB AUTO - BPMIS AUTOMATION
echo ============================================================================
echo Start Time: %date% %time%
echo ============================================================================
echo.

:: Check if Python executable exists
if not exist "%PYTHON_EXE%" (
    echo ❌ ERROR: Python executable not found!
    echo Path: %PYTHON_EXE%
    echo.
    echo Please update the PYTHON_EXE path in this batch file to point to your
    echo ArcGIS Pro Python installation.
    echo.
    pause
    exit /b 1
)

:: Check if scripts exist
if not exist "%SCRIPT_DIR%\daily_bpmis_update.py" (
    echo ❌ ERROR: daily_bpmis_update.py not found in %SCRIPT_DIR%
    echo Please place the Python scripts in the correct directory.
    echo.
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%\sync_approvals.py" (
    echo ❌ ERROR: sync_approvals.py not found in %SCRIPT_DIR%
    echo Please place the Python scripts in the correct directory.
    echo.
    pause
    exit /b 1
)

:: ============================================================================
:: STEP 1: Update BPMIS_Current Table with API Data
:: ============================================================================
echo 🔄 STEP 1: UPDATING BPMIS_CURRENT TABLE...
echo.

cd /d "%SCRIPT_DIR%"
"%PYTHON_EXE%" "daily_bpmis_update.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERROR: Permit update failed with exit code: %ERRORLEVEL%
    echo Stopping automation process.
    echo.
    pause
    exit /b %ERRORLEVEL%
) else (
    echo.
    echo ✅ SUCCESS: BPMIS_Current table updated successfully!
)

:: Small delay between steps
echo.
echo Waiting 3 seconds before next step...
timeout /t 3 /nobreak >nul

:: ============================================================================
:: STEP 2: Sync Approval Status to Parcels
:: ============================================================================
echo.
echo 🔄 STEP 2: SYNCING APPROVAL STATUS TO PARCELS...
echo.

"%PYTHON_EXE%" "sync_approvals.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ ERROR: Approval sync failed with exit code: %ERRORLEVEL%
    echo BPMIS_Current was updated, but parcel sync failed.
    echo.
    pause
    exit /b %ERRORLEVEL%
) else (
    echo.
    echo ✅ SUCCESS: Approval status synchronized successfully!
)

:: ============================================================================
:: COMPLETION SUMMARY
:: ============================================================================
echo.
echo ============================================================================
echo                            🎉 AUTOMATION COMPLETE!
echo ============================================================================
echo End Time: %date% %time%
echo.
echo ✅ STEP 1: BPMIS_Current table updated from API
echo ✅ STEP 2: Approval status synchronized to parcels  
echo.
echo The BPMIS permit management process has completed successfully.
echo All permits have been updated and synchronized.
echo.
echo 📁 Log file saved to: %LOG_FILE%
echo ============================================================================
echo.

:: Log completion
echo. >> "%LOG_FILE%"
echo AUTOMATION COMPLETED SUCCESSFULLY: %date% %time% >> "%LOG_FILE%"
echo ============================================================================ >> "%LOG_FILE%"

:: Clean up old log files (keep only last 30 days)
forfiles /p "%LOG_DIR%" /s /m *.log /d -30 /c "cmd /c del @path" 2>nul

echo Press any key to exit...
pause >nul
exit /b 0
@echo off
title Reacthon Dashboard Data Updater
color 0A

echo ===================================================
echo     Yer-Tai Dashboard Data Ingestion Tool
echo ===================================================
echo.
echo This tool will:
echo 1. Process raw Excel sheets inside the "data" folder.
echo 2. Generate clean CSV files.
echo 3. Automatically load them into the active dashboard.
echo 4. Offer to upload them to your live Streamlit Cloud site.
echo.
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system's PATH.
    echo Please install Python and make sure it is added to your PATH.
    pause
    exit
)

:: Verify virtual environment exists
if not exist "%~dp0final_version\copper_dashboard\.venv" (
    echo [INFO] Virtual environment not found. Building environment first...
    echo [INFO] This might take a minute...
    cd /d "%~dp0final_version\copper_dashboard"
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip -q
    pip install -r requirements.txt
    cd /d "%~dp0"
)

:: Activate the environment
echo [1/4] Activating environment...
call "%~dp0final_version\copper_dashboard\.venv\Scripts\activate.bat"
echo [STATUS] Environment activated.
echo.

:: 1. Parse Tech Journal
echo [2/4] Parsing Technical Journal Excel sheet...
python "%~dp0parser_tech_journal.py"
if %errorlevel% neq 0 (
    echo [WARNING] Technical Journal parser encountered an issue or finished with warnings.
)
echo.

:: 2. Parse Downtime
echo [3/4] Parsing Downtime Excel sheet...
python "%~dp0parse_downtime.py"
if %errorlevel% neq 0 (
    echo [WARNING] Downtime parser encountered an issue or finished with warnings.
)
echo.

:: 3. Parse Water Data
echo [4/4] Parsing Water Data Excel sheet...
python "%~dp0water_to_csv_convo.py"
if %errorlevel% neq 0 (
    echo [WARNING] Water parser encountered an issue or finished with warnings.
)
echo.

echo ===================================================
echo     Copying Clean CSVs to Dashboard Data Folder
echo ===================================================
echo.

:: Ensure destination directories exist
if not exist "%~dp0final_version\copper_dashboard\data" mkdir "%~dp0final_version\copper_dashboard\data"

:: Copy files
copy /Y "%~dp0output\tech_journal.csv" "%~dp0final_version\copper_dashboard\data\tech_journal.csv" >nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Technical Journal data successfully updated.
) else (
    echo [ERROR] Failed to copy Technical Journal data!
)

copy /Y "%~dp0downtime_data.csv" "%~dp0final_version\copper_dashboard\data\downtime.csv" >nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Downtime data successfully updated.
) else (
    echo [ERROR] Failed to copy Downtime data!
)

copy /Y "%~dp0output\extracted_tables_clean.csv" "%~dp0final_version\copper_dashboard\data\water.csv" >nul
if %errorlevel% equ 0 (
    echo [SUCCESS] Water consumption data successfully updated.
) else (
    echo [ERROR] Failed to copy Water consumption data!
)

echo.
echo ===================================================
echo     Local Import Complete!
echo ===================================================
echo.
echo If your local dashboard is running, the screen will reload
echo and display the new data automatically in a few seconds!
echo.

:: Git integration for Streamlit Cloud
echo ===================================================
echo     Push to Live Streamlit Cloud
echo ===================================================
echo.
set /p push=Do you want to upload this new data to your live Streamlit Cloud website? (y/n): 

if /I "%push%"=="y" (
    echo.
    echo [INFO] Preparing data files for upload...
    git add "%~dp0final_version/copper_dashboard/data/"
    git commit -m "Update live dashboard data from Excel sheets"
    echo [INFO] Pushing files to GitHub...
    git push origin main
    if %errorlevel% equ 0 (
        echo.
        echo [SUCCESS] Live website updated! 
        echo Streamlit will reload the new data in about 10-20 seconds.
    ) else (
        echo [ERROR] Failed to push to GitHub. Please check your internet connection or git login.
    )
) else (
    echo [INFO] Live site was not updated. Local changes are preserved.
)

echo.
echo Press any key to exit.
pause >nul

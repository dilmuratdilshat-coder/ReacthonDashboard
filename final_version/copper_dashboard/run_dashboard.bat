@echo off
title Reacthon Dashboard Launcher
color 0B

echo ===================================================
echo     Yer-Tai Enrichment Plant Dashboard Launcher
echo ===================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system's PATH.
    echo.
    echo To run this dashboard, you need to install Python (3.9 to 3.12 recommended).
    echo.
    echo IMPORTANT: During Python installation, make sure to check the box that says:
    echo            "Add Python to PATH" or "Add python.exe to PATH"
    echo.
    echo Opening Python download page in your browser...
    start https://www.python.org/downloads/
    echo.
    echo Press any key to exit after installing Python, then run this file again.
    pause >nul
    exit
)

echo [1/3] Checking python virtual environment...
if not exist .venv (
    echo [INFO] Virtual environment (.venv) not found. Creating a new one...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit
    )
)
echo [STATUS] Virtual environment is ready.
echo.

echo [2/3] Activating virtual environment and verifying packages...
call .venv\Scripts\activate.bat

:: Upgrade pip and install requirements
python -m pip install --upgrade pip -q
echo [INFO] Installing required packages (Streamlit, Pandas, Plotly, PyYAML)...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit
)
echo [STATUS] Packages successfully verified.
echo.

echo [3/3] Starting the Yer-Tai Streamlit Dashboard...
echo [INFO] Streamlit will open a browser window automatically.
echo.
streamlit run app.py

pause

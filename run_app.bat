@echo off
REM Oracle Lookup Management System - App Launcher
REM Starts the Oracle-backed Streamlit application using the local virtual environment.

setlocal

cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo ERROR: Virtual environment not found.
    echo Run setup.bat first to create the environment and install dependencies.
    echo.
    pause
    exit /b 1
)

echo.
echo =========================================
echo Starting Oracle Lookup Manager
echo =========================================
echo.

call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    echo.
    pause
    exit /b 1
)

python create_schema.py
if %errorlevel% neq 0 (
    echo ERROR: Oracle schema check failed.
    echo Verify your Oracle connection settings in create_schema.py and app.py.
    echo.
    pause
    exit /b 1
)

echo.
echo The application will open at: http://localhost:8501
echo Press Ctrl+C to stop the server.
echo.

streamlit run app.py

pause
@echo off
REM Oracle Lookup Management System - Setup Script
REM This script sets up the Python environment and runs the application

setlocal enabledelayedexpansion

echo.
echo =========================================
echo Oracle Lookup Management System Setup
echo =========================================
echo.

REM Change to project directory
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo SOLUTION 1: Install Python from https://www.python.org/downloads/
    echo   - Download Python 3.11+
    echo   - IMPORTANT: Check "Add Python to PATH" during installation
    echo   - Restart your terminal after installation
    echo.
    echo SOLUTION 2: Use Chocolatey to install Python:
    echo   choco install python
    echo.
    echo SOLUTION 3: Use Windows Package Manager:
    echo   winget install Python.Python.3.11
    echo   (May need to restart terminal after installation)
    echo.
    pause
    exit /b 1
)

echo [OK] Python found: 
python --version

REM Create virtual environment
echo.
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated

REM Install dependencies
echo.
echo Installing dependencies...
pip install --upgrade pip setuptools wheel
pip install --only-binary :all: -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies with binary wheels
    echo Attempting alternative installation...
    pip install streamlit==1.31.1
    pip install oracledb==1.4.1
    pip install pandas==1.5.3
    pip install python-dateutil==2.8.2
    if %errorlevel% neq 0 (
        echo ERROR: Installation failed
        echo Please manually run: pip install -r requirements.txt
        pause
        exit /b 1
    )
)
echo [OK] Dependencies installed

REM Initialize database schema
echo.
echo Initializing database schema...
python create_schema.py
if %errorlevel% neq 0 (
    echo ERROR: Failed to initialize database
    echo Please check your Oracle connection settings in create_schema.py
    pause
    exit /b 1
)
echo [OK] Database schema initialized

REM Launch Streamlit application
echo.
echo =========================================
echo Launching Oracle Lookup Manager...
echo =========================================
echo.
echo The application will open at: http://localhost:8501
echo Press Ctrl+C to stop the server
echo.

streamlit run app.py

pause

@echo off
echo.
echo ===============================================
echo  Vehicle Log Channel Appender - Modern Edition
echo ===============================================
echo.
echo Starting application...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from python.org
    pause
    exit /b 1
)

REM Check if CustomTkinter is installed
python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo CustomTkinter not found. Installing dependencies...
    pip install -r requirements_modern.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        echo Please run: pip install -r requirements_modern.txt
        pause
        exit /b 1
    )
)

REM Launch the application
echo Launching Vehicle Log Channel Appender...
python vehicle_log_channel_appender_modern.py

REM Pause on error
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code %errorlevel%
    pause
)
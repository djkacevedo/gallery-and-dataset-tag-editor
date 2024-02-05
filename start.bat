@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Change directory to the script's directory
cd /d %~dp0

REM Set the virtual environment directory
SET VENV_DIR=venv

REM Check if the virtual environment exists, if not create it
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
)

REM Activate the virtual environment
CALL "%VENV_DIR%\Scripts\activate.bat"

REM Check if requirements.txt is updated, install dependencies
if exist requirements.txt (
    echo Installing requirements...
    pip install -r requirements.txt
)

REM Run the application
echo Starting application...
python app.py

REM Deactivate the virtual environment on exit
CALL "%VENV_DIR%\Scripts\deactivate.bat"

ENDLOCAL

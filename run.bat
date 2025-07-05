@echo off
:: run.bat - Standardized script to run The Foundry application

echo Stopping any existing Flask processes on port 5000...
:: Find and kill processes on port 5000 (Windows compatible)
for /f "tokens=5" %%p in ('netstat -aon ^| findstr :5000') do (
    if not "%%p"=="" (
        taskkill /F /PID %%p >nul 2>nul
    )
)
:: Give it a moment to clear
ping -n 2 127.0.0.1 >nul

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting The Foundry application...
python app.py

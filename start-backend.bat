@echo off
echo ============================================================
echo Starting Backend Server with Fixed CORS Configuration
echo ============================================================
echo.

cd /d "%~dp0backend"

echo Activating virtual environment...
call ..\venv\Scripts\activate.bat

echo.
echo Starting Flask server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

python main.py

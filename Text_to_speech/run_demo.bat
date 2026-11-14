@echo off
rem Double-click to start the TTS demo. The first run sets up Python packages (a few minutes).
cd /d "%~dp0"

if not exist ".venv\installed.ok" (
    echo Setting up the Python environment - first run only...
    if not exist ".venv\Scripts\python.exe" (
        py -3 -m venv .venv 2>nul || python -m venv .venv
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Package installation failed. Check your internet connection and run this file again.
        pause
        exit /b 1
    )
    echo ok> ".venv\installed.ok"
)

if not exist ".env" copy ".env.example" ".env" >nul

echo Starting the demo at http://127.0.0.1:7860  (close this window to stop it)
".venv\Scripts\python.exe" app\gradio_tts_demo.py
pause

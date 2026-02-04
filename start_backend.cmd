@echo off
cd /d "%~dp0backend"
echo Starting Backend...

:: Check if uv is installed
where uv >nul 2>nul
if %errorlevel% equ 0 (
    echo Using uv to run backend...
    echo Syncing dependencies...
    call uv sync
    call uv run main.py
) else (
    echo uv not found. Checking for virtual environment...
    if exist ".venv\Scripts\activate.bat" (
        echo Activating virtual environment...
        call .venv\Scripts\activate.bat
        echo Installing/Updating dependencies...
        call pip install -e .
        python main.py
    ) else (
        echo No virtual environment found. Trying system python...
        echo Installing/Updating dependencies...
        call pip install -e .
        python main.py
    )
)
pause

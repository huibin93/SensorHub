@echo off
cd /d "%~dp0frontend"

echo Installing Frontend Dependencies...
call npm install

echo Starting Frontend...
npm run dev
pause

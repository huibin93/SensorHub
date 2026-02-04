@echo off
echo Starting SensorHub Project...

start "SensorHub Backend" cmd /c "%~dp0start_backend.cmd"
start "SensorHub Frontend" cmd /c "%~dp0start_frontend.cmd"

echo Both services started in separate windows.

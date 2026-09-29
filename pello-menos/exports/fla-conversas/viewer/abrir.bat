@echo off
cd /d "%~dp0"
echo Abrindo servidor em http://localhost:8765
start "" "http://localhost:8765"
python -m http.server 8765

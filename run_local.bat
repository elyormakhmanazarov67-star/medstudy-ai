@echo off
chcp 65001 > nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Avval setup_windows.bat faylini ishga tushiring.
 pause
 exit /b 1
)
call .venv\Scripts\activate.bat
echo Mahalliy sinov manzili: http://127.0.0.1:8000/?demo=1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause

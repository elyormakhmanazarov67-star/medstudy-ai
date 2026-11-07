@echo off
chcp 65001 > nul
cd /d "%~dp0"
where py >nul 2>nul
if not %errorlevel%==0 (
 echo Python topilmadi. Python 3.10+ o'rnating.
 pause
 exit /b 1
)
py -m venv .venv
if errorlevel 1 (pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env >nul
if not exist data mkdir data
echo.
echo Tayyor. .env faylini ochib TOKEN, WEB_APP_URL va ruxsatli Telegram IDlarni kiriting.
echo Lokal demonstratsiya uchun DEV_PREVIEW=1 sozlang, keyin run_local.bat ni oching.
pause

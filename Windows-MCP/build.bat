@echo off
cd /d "%~dp0"
chcp 65001 > nul
title Lotus Build System

echo.
echo ============================================
echo    LOTUS BUILD SYSTEM v2.0
echo ============================================
echo.

echo [1/4] Installing dependencies...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo      Pip not found. Attempting to restore via ensurepip...
    python -m ensurepip --upgrade >nul 2>&1
    python -m pip --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo      ensurepip failed. Downloading get-pip.py...
        powershell -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py"
        python get-pip.py --quiet
        del get-pip.py
    )
)
python -m pip install pyinstaller --quiet
python -m pip install -r requirements.txt --quiet
echo      Done.

echo [2/4] Cleaning old build files...
if exist dist\Lotus.exe del /f /q dist\Lotus.exe
if exist build rd /s /q build
if exist Lotus.spec del /f /q Lotus.spec
echo      Done.

echo [3/4] Building Lotus.exe...
python -m PyInstaller ^
  --onefile ^
  --noconsole ^
  --icon=assets\lotus_icon.ico ^
  --name=Lotus ^
  --add-data "assets;assets" ^
  --add-data "src;src" ^
  --paths "src" ^
  --hidden-import=windows_mcp.telegram_bot ^
  --hidden-import=dotenv ^
  --hidden-import=pystray ^
  --hidden-import=PIL._tkinter_finder ^
  --hidden-import=customtkinter ^
  --hidden-import=psutil ^
  --hidden-import=telegram ^
  --hidden-import=telegram.ext ^
  --hidden-import=yt_dlp ^
  --hidden-import=rich ^
  --hidden-import=requests ^
  --hidden-import=thefuzz ^
  --hidden-import=thefuzz.fuzz ^
  --hidden-import=pyperclip ^
  --collect-data=customtkinter ^
  app.py

if not exist dist\Lotus.exe (
  echo.
  echo [ERROR] Build failed! Check output above.
  pause
  exit /b 1
)

echo [4/4] Build complete!
echo.
echo Output  : dist\Lotus.exe
echo Next    : Open installer.iss in Inno Setup Compiler
echo          to generate the final LotusSetup.exe installer
echo.
pause

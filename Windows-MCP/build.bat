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
  --hidden-import=pystray._win32 ^
  --hidden-import=PIL.Image ^
  --collect-data=customtkinter ^
  app.py

if not exist dist\Lotus.exe (
  echo.
  echo [ERROR] Lotus.exe build failed! Check output above.
  if not defined CI pause
  exit /b 1
)

echo [4/5] Building LotusTray.exe ...
python -m PyInstaller ^
  --onefile ^
  --noconsole ^
  --icon=assets\lotus_icon.ico ^
  --name=LotusTray ^
  --add-data "assets;assets" ^
  --add-data "src;src" ^
  --add-data "version.json;." ^
  --add-data "bot_service.py;." ^
  --paths "src" ^
  --hidden-import=pystray._win32 ^
  --hidden-import=PIL.Image ^
  --hidden-import=psutil ^
  --hidden-import=requests ^
  --hidden-import=windows_mcp.updater ^
  lotus_tray.py

if not exist dist\LotusTray.exe (
  echo.
  echo [ERROR] LotusTray.exe build failed!
  if not defined CI pause
  exit /b 1
)

echo [5/5] Build complete!
echo.
echo Outputs:
echo   dist\Lotus.exe
echo   dist\LotusTray.exe
echo Next: open installer.iss in Inno Setup Compiler
echo       to generate the final LotusSetup.exe installer
echo.
if not defined CI pause

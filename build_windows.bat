@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python.
  echo Instala Python 3 desde python.org y marca "Add Python to PATH".
  pause
  exit /b 1
)

python -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo No se pudo instalar PyInstaller.
  pause
  exit /b 1
)

python -m PyInstaller --noconfirm --clean --onefile --windowed --name APC40_MK2_LED_Mapper APC40_MK2_LED_Mapper.py

echo.
echo ---------------------------------------------
echo EXE creado en:
echo %~dp0dist\APC40_MK2_LED_Mapper.exe
echo ---------------------------------------------
pause

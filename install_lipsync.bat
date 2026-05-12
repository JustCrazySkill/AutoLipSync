@echo off
title Auto LipSync v5.1 — Installer
color 0B

echo.
echo  =====================================================
echo       AUTO LIPSYNC v5.1  --  INSTALLER
echo  =====================================================
echo.

set PYTHON_EXE=

:: 1. Standard commands
python --version >nul 2>&1
if %errorlevel% == 0 ( set PYTHON_EXE=python & goto :found )

python3 --version >nul 2>&1
if %errorlevel% == 0 ( set PYTHON_EXE=python3 & goto :found )

py --version >nul 2>&1
if %errorlevel% == 0 ( set PYTHON_EXE=py & goto :found )

:: 2. Common installation paths
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "C:\Python39\python.exe"
    "C:\Program Files\Python313\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Program Files\Python39\python.exe"
    "C:\Program Files (x86)\Python312\python.exe"
    "C:\Program Files (x86)\Python311\python.exe"
    "C:\Program Files (x86)\Python310\python.exe"
) do (
    if exist %%P ( set PYTHON_EXE=%%P & goto :found )
)

:: 3. Windows Store path
for %%P in (
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
    "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe"
) do (
    if exist %%P ( set PYTHON_EXE=%%P & goto :found )
)

:: 4. Search user folder
echo  Searching your system for Python...
for /f "delims=" %%F in ('where /r "%USERPROFILE%" python.exe 2^>nul') do (
    set PYTHON_EXE=%%F
    goto :found
)

:: Not found
echo.
echo  [ERROR] Python was not found on this computer!
echo.
echo  Download and install Python 3.9+ from:
echo    https://www.python.org/downloads/
echo.
echo  IMPORTANT: Check the box during install:
echo    [x] Add Python to PATH
echo.
echo  Then run this installer again.
echo.
pause
exit /b 1

:found
echo  Python found: %PYTHON_EXE%
%PYTHON_EXE% --version
echo.

%PYTHON_EXE% -c "import sys; exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python 3.9+ required! Please update Python.
    pause
    exit /b 1
)

echo  Starting installer...
echo.
%PYTHON_EXE% "%~dp0install_lipsync.py"

pause

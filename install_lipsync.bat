@echo off
title Auto LipSync v5.1 — Installer
color 0B

echo.
echo  =====================================================
echo       AUTO LIPSYNC v5.1  --  INSTALLER
echo  =====================================================
echo.

set PYTHON_EXE=

:: === 1. Ищем КОНКРЕТНЫЕ версии 3.9–3.13 (в обратном порядке, сначала свежие) ===
for %%V in (313 312 311 310 39) do (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        "C:\Python%%V\python.exe"
        "C:\Program Files\Python%%V\python.exe"
        "C:\Program Files (x86)\Python%%V\python.exe"
    ) do (
        if exist %%P (
            set PYTHON_EXE=%%P
            goto :check_ver
        )
    )
)

:: === 2. Проверяем py launcher с приоритетом 3.11–3.9 ===
for %%V in (3.13 3.12 3.11 3.10 3.9) do (
    py -%%V --version >nul 2>&1
    if !errorlevel! == 0 (
        set PYTHON_EXE=py -%%V
        goto :check_ver
    )
)

:: === 3. Если py не сработал — проверяем стандартные команды, но ОТСЕИВАЕМ 3.14+ ===
for %%C in (python python3) do (
    %%C --version >nul 2>&1
    if !errorlevel! == 0 (
        %%C -c "import sys; exit(0 if sys.version_info < (3,14) else 1)" >nul 2>&1
        if !errorlevel! == 0 (
            set PYTHON_EXE=%%C
            goto :check_ver
        )
    )
)

:: === 4. Поиск вручную по папкам пользователя (тоже с фильтром) ===
echo  Searching your system for Python 3.9–3.13...
for /f "delims=" %%F in ('where /r "%USERPROFILE%" python.exe 2^>nul') do (
    "%%F" -c "import sys; exit(0 if (3,9) <= sys.version_info < (3,14) else 1)" >nul 2>&1
    if !errorlevel! == 0 (
        set PYTHON_EXE=%%F
        goto :check_ver
    )
)

:: === Не найдено ===
echo.
echo  [ERROR] Python 3.9–3.13 not found on this computer!
echo.
echo  You have Python 3.14, but WhisperX needs 3.9–3.13.
echo.
echo  Download and install Python 3.11 or 3.12 from:
echo    https://www.python.org/downloads/windows/
echo.
echo  IMPORTANT: Check the box during install:
echo    [x] Add Python to PATH
echo.
echo  Then run this installer again.
echo.
pause
exit /b 1

:check_ver
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
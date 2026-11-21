@echo off
setlocal enableextensions
cd /d "%~dp0"
set PYTHONUTF8=1

echo [ASHA Demo] Locating Python...
if exist "backend\.venv\Scripts\python.exe" (
    "backend\.venv\Scripts\python.exe" start_demo.py %*
    goto :done
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 -V >nul 2>nul
    if %errorlevel%==0 (
        py -3.12 start_demo.py %*
        goto :done
    )
    py -3 start_demo.py %*
    goto :done
)

where python >nul 2>nul
if %errorlevel%==0 (
    python start_demo.py %*
    goto :done
)

echo [ERROR] Python 3.12+ not found in PATH. Install Python 3.12 from https://www.python.org/downloads/ and check "Add Python to PATH".
pause
exit /b 1

:done
if %errorlevel% neq 0 (
    echo.
    echo [ASHA Demo] Exited with error code %errorlevel%.
    pause
)
exit /b %errorlevel%


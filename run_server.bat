@echo off
cd /d "%~dp0"

if not exist "%~dp0venv\Scripts\python.exe" (
    echo ERRO: a virtualenv nao foi encontrada em "%~dp0venv"
    pause
    exit /b 1
)

"%~dp0venv\Scripts\python.exe" -u run_server.py

if errorlevel 1 (
    echo.
    echo O servidor foi encerrado com erro.
    pause
)

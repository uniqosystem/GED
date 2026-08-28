@echo off
cd /d "%~dp0"

if not exist "%~dp0venv\Scripts\python.exe" (
	echo ERRO: a virtualenv nao foi encontrada em "%~dp0venv"
	exit /b 1
)

"%~dp0venv\Scripts\python.exe" -u "%~dp0run_server.py"
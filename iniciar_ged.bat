@echo off
:: Forçar a entrada na pasta do projeto
cd /d C:\GED_CRFPB

:: Ativar a venv explicitamente
call C:\GED_CRFPB\venv\Scripts\activate.bat

:: Rodar o servidor apontando para todas as interfaces (0.0.0.0)
python manage.py runserver 0.0.0.0:8000
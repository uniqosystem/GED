@echo off
:: Define a data para criar pastas únicas (Ex: 2026-07)
set data=%date:~-4%-%date:~3,2%

:: Cria as pastas de destino com a data, mantendo o histórico
robocopy "D:\SETORES" "J:\Backup_Mensal\%data%\SETORES" /E /R:3 /W:5 /NP /LOG:"J:\Logs\log_mensal_setores_%data%.txt"
robocopy "D:\GED" "J:\Backup_Mensal\%data%\GED" /E /R:3 /W:5 /NP /LOG:"J:\Logs\log_mensal_ged_%data%.txt"
robocopy "D:\GED_LIXEIRA" "J:\Backup_Mensal\%data%\GED_LIXEIRA" /E /R:3 /W:5 /NP /LOG:"J:\Logs\log_mensal_lixeira_%data%.txt"
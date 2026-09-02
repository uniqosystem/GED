@echo off
set data=%date:~-4%-%date:~3,2%

if not exist "J:\Logs" mkdir "J:\Logs"

robocopy "D:\SETORES" "J:\Backup_Mensal\%data%\SETORES" /E /R:3 /W:5 /NP /LOG:"J:\Logs\log_mensal_setores_%data%.txt"
robocopy "D:\GED" "J:\Backup_Mensal\%data%\GED" /E /R:3 /W:5 /NP /LOG:"J:\Logs\log_mensal_ged_%data%.txt"
robocopy "D:\GED_LIXEIRA" "J:\Backup_Mensal\%data%\GED_LIXEIRA" /E /R:3 /W:5 /NP /LOG:"J:\Logs\log_mensal_lixeira_%data%.txt"
robocopy "D:\TRAMITACAO" "J:\Backup_Mensal\%data%\TRAMITACAO" /E /R:3 /W:5 /NP /LOG:"J:\Logs\log_mensal_tramitacao_%data%.txt"
robocopy "D:\PONTO" "J:\Backup_Mensal\%data%\PONTO" /E /R:3 /W:5 /NP /LOG:"J:\Logs\log_mensal_ponto_%data%.txt"

if not exist "J:\Backup_Mensal\%data%\GED" mkdir "J:\Backup_Mensal\%data%\GED"
copy /Y "C:\GED_CRFPB\db.sqlite3" "J:\Backup_Mensal\%data%\GED\db.sqlite3" >> "J:\Logs\log_mensal_banco_%data%.txt"
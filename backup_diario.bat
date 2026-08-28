@echo off
if not exist "J:\Logs" mkdir "J:\Logs"

robocopy "D:\SETORES" "J:\SETORES" /MIR /R:3 /W:5 /NP /LOG:"J:\Logs\log_setores.txt"
robocopy "D:\GED" "J:\GED" /MIR /R:3 /W:5 /NP /LOG:"J:\Logs\log_ged.txt"
robocopy "D:\GED_LIXEIRA" "J:\GED_LIXEIRA" /MIR /R:3 /W:5 /NP /LOG:"J:\Logs\log_lixeira.txt"
robocopy "D:\TRAMITACAO" "J:\TRAMITACAO" /MIR /R:3 /W:5 /NP /LOG:"J:\Logs\log_tramitacao.txt"

copy /Y "C:\GED_CRFPB\db.sqlite3" "J:\GED\db.sqlite3" >> "J:\Logs\log_banco.txt"

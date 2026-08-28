@echo off
:: O Robocopy deve apontar para as pastas raiz de cada setor
:: Exemplo para a pasta SETORES
robocopy "D:\SETORES" "J:\SETORES" /MIR /R:3 /W:5 /NP /LOG:"J:\Logs\log_setores.txt"

:: Exemplo para a pasta GED (que estava em C, mas agora vamos supor que esteja em D)
robocopy "D:\GED" "J:\GED" /MIR /R:3 /W:5 /NP /LOG:"J:\Logs\log_ged.txt"

:: Exemplo para a lixeira
robocopy "D:\GED_LIXEIRA" "J:\GED_LIXEIRA" /MIR /R:3 /W:5 /NP /LOG:"J:\Logs\log_lixeira.txt"

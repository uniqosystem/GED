# Backups operacionais

## Estado atual

Os scripts `backup_diario.bat` e `backup_mensal.bat` permanecem na raiz por compatibilidade com possiveis referencias externas, como o Agendador de Tarefas do Windows.

Este notebook e um ambiente de correcao e desenvolvimento. As raizes corretas do GED, dos setores, da lixeira, da tramitacao e dos backups serao informadas na implantacao no computador de producao; os caminhos locais deste ambiente nao devem ser usados como referencia operacional.

Eles usam estes caminhos fixos:

- origem: `D:\SETORES`, `D:\GED`, `D:\GED_LIXEIRA`, `D:\TRAMITACAO`, `D:\EVENTOS`, `D:\ECARTA` e `D:\PONTO`;
- destino diario: `J:\SETORES`, `J:\GED`, `J:\GED_LIXEIRA`, `J:\TRAMITACAO`, `J:\EVENTOS`, `J:\ECARTA` e `J:\PONTO`;
- destino mensal: `J:\Backup_Mensal\AAAA-MM\...`;
- logs: `J:\Logs\...` (incluindo `ponto.log` dentro do backup de `D:\PONTO`).

Esses caminhos sao configuracao operacional do servidor, nao defaults portaveis da aplicacao.

## Eventos e e-Carta

As imagens e certificados de eventos ficam em subpastas por evento dentro de `EVENTOS_DIR`; os scripts copiam `D:\EVENTOS` separadamente. Cada conversao e-Carta persiste os arquivos de servico e resposta em `ECARTA_DIR/lotes/<numero-do-lote>/`; os scripts copiam `D:\ECARTA` separadamente. O banco tambem precisa ser restaurado junto para preservar os registros e os caminhos dos lotes.

Na primeira implantacao, arquivos de eventos existentes em `TRAMITACAO_DIR/eventos` precisam ser copiados preservando a estrutura para `EVENTOS_DIR/eventos` antes da troca de configuracao. Use uma copia sem espelhamento destrutivo e confira a quantidade de arquivos antes/depois. O e-Carta anterior mantinha os resultados somente na sessao, portanto esses lotes antigos nao existem para migrar.

Ao implantar em outro servidor, configure `EVENTOS_DIR` e `ECARTA_DIR` e atualize os scripts de backup para usar as mesmas raizes. Nao considere os defaults `D:\...` dos scripts como portaveis. A rotina ainda precisa de validacao de retorno do `robocopy` e de um teste periodico de restauracao conjunta do banco, `EVENTOS_DIR` e `ECARTA_DIR`.

## Riscos conhecidos

- `/MIR` no backup diario espelha exclusoes da origem no destino. Uma exclusao acidental na origem pode ser propagada ao backup.
- O banco e copiado com `copy` enquanto a aplicacao pode estar ativa; essa copia simples nao garante consistencia do SQLite. Use o comando de backup do SQLite ou pare/quiesca a aplicacao durante a copia.
- `robocopy` pode retornar codigos de saida diferentes de zero mesmo quando parte da operacao foi concluida; os scripts nao fazem tratamento ou alerta desses codigos.
- A data mensal usa `%date%`, cujo formato depende da localizacao do Windows.
- Nao foi possivel confirmar referencias do Agendador de Tarefas a partir do repositorio.

## Proposta segura

Antes de mover ou alterar os scripts:

1. Confirmar se o Agendador de Tarefas aponta para os caminhos atuais.
2. Confirmar os caminhos reais de origem, destino e logs no servidor.
3. Definir se o banco SQLite deve ser copiado e em qual politica de retencao.
4. Definir se `/MIR` e realmente desejado ou se o backup diario deve ser incremental/versionado.
5. Testar restauracao de pelo menos um GED, uma pasta de setor, a lixeira e o banco.

A reorganizacao futura pode mover os scripts para `ops/backup/`, mantendo wrappers na raiz enquanto referencias externas nao forem atualizadas.

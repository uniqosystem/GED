# Backups operacionais

## Estado atual

Os scripts `backup_diario.bat` e `backup_mensal.bat` permanecem na raiz por compatibilidade com possiveis referencias externas, como o Agendador de Tarefas do Windows.

Este notebook e um ambiente de correcao e desenvolvimento. As raizes corretas do GED, dos setores, da lixeira, da tramitacao e dos backups serao informadas na implantacao no computador de producao; os caminhos locais deste ambiente nao devem ser usados como referencia operacional.

Eles usam estes caminhos fixos:

- origem: `D:\SETORES`, `D:\GED` e `D:\GED_LIXEIRA`;
- destino diario: `J:\SETORES`, `J:\GED` e `J:\GED_LIXEIRA`;
- destino mensal: `J:\Backup_Mensal\AAAA-MM\...`;
- logs: `J:\Logs\...`.

Esses caminhos sao diferentes dos defaults de desenvolvimento em `.env.example` e nao existem no ambiente auditado. Eles devem ser tratados como configuracao do servidor, nao como caminhos portaveis da aplicacao.

## Riscos conhecidos

- `/MIR` no backup diario espelha exclusoes da origem no destino. Uma exclusao acidental na origem pode ser propagada ao backup.
- Os scripts nao fazem copia explicita do `db.sqlite3`.
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

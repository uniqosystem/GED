# Arquitetura do GED_CRFPB

## Stack

O sistema usa Python, Django, SQLite, Django Templates, Bootstrap e JavaScript vanilla. Os apps Django atuais sao `core`, `tramitacao` e `ecarta`; `setup` concentra a configuracao do projeto.

## Fronteiras dos modulos

- `core`: autenticacao, perfis, setores, documentos do GED, filesystem, uploads, lixeira e auditoria.
- `tramitacao`: fluxo de documentos entre setores, destinatarios, status, respostas, devolucoes, assinaturas, historico e anexos.
- `ecarta`: importacao de planilhas, geracao dos arquivos de lote e downloads.
- `setup`: settings, URLs raiz, WSGI e ASGI.

`tramitacao` e `ecarta` podem consumir modelos e validadores do `core`. O `core` nao deve depender dos demais apps.

## Reorganizacao incremental

A reorganizacao preserva os nomes dos apps, URLs, modelos, migrations, chaves de sessao, caminhos de upload e contratos dos endpoints. Novas camadas sao introduzidas por responsabilidade, mantendo wrappers de compatibilidade quando necessario.

Ordem adotada:

1. Separar consultas de leitura das regras de negocio.
2. Separar services de dominio por responsabilidade.
3. Extrair views e formularios por fluxo.
4. Extrair JavaScript e includes de template.
5. Reorganizar `core` e `ecarta` depois de cobrir os contratos existentes.

## Consultas de tramitacao

`tramitacao/queries.py` concentra consultas reutilizaveis de leitura: caixa de entrada e usuarios por setor. `tramitacao/attachments.py` concentra resolucao de uploads, validacao e persistencia de anexos. As regras de transicao e mutacao permanecem separadas nos services de dominio.

`tramitacao/services.py` funciona como fachada de compatibilidade; as implementacoes ficam em `queries.py`, `workflow.py`, `dispatch.py`, `responses.py`, `signatures.py`, `permissions.py`, `history.py` e `attachments.py`.

No `ecarta`, o processamento de planilhas e geracao dos arquivos de lote ficam em `ecarta/services.py`; a view preserva apenas o fluxo HTTP, mensagens, sessao e downloads.

No `core`, autenticacao e sessao foram extraidas para `core/auth_views.py`. `core.views` continua reexportando os nomes usados pelas URLs, enquanto as operacoes de filesystem permanecem em migracao.

Os helpers de filesystem usados pela navegacao e pelos uploads estao em `core/file_services.py`. As consultas de diretório ficam em `core/file_queries.py`; a entrega de arquivos fica em `core/file_delivery.py`; a configuração de módulos e breadcrumbs fica em `core/navigation_services.py`; a criação de subpastas fica em `core/storage_services.py`. A movimentacao e restauracao da lixeira ficam em `core/trash_services.py`; a listagem fica em `core/trash_queries.py`; a consulta de auditoria fica em `core/audit_queries.py`; as views preservam apenas o fluxo HTTP, mensagens e filtros de entrada.

Os arquivos estaticos-fonte compartilhados ficam em `static/`; `core/static/` nao deve duplicar esses assets. `staticfiles/` e a saida de `collectstatic` definida por `STATIC_ROOT` e nao deve ser editada como fonte.

Os modelos do `core` estao separados em `core/models/access.py`, `documents.py`, `audit.py` e `trash.py`; `core/models/__init__.py` preserva a API `core.models` e o signal de perfil fica em `core/models/signals.py`.

Os modelos da `tramitacao` estao separados em `tramitacao/models/workflow.py` e `tramitacao/models/attachments.py`; `tramitacao/models/__init__.py` preserva a API `tramitacao.models`.

Componentes de interface da tramitacao devem ser extraidos gradualmente para `templates/tramitacao/includes/`, preservando IDs, nomes de campos, URLs e contratos JavaScript existentes.

As abas de recebidos, enviados, arquivados e concluidos agora possuem includes proprios. O formulario de acoes em lote continua no template da caixa e envolve apenas as tres abas que suportam essas acoes.

## Validacao

Cada etapa deve passar por:

- `python manage.py check`
- `python manage.py test tramitacao`
- testes de integracao dos apps afetados
- verificacao de rotas, templates, uploads e sessoes quando a etapa os tocar

Nao remover arquivos duplicados, modelos ou aliases sem localizar referencias e validar os testes correspondentes.

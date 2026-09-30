# Modulos do GED_CRFPB

## Core

O app `core` e a base compartilhada do sistema. Ele possui autenticacao, perfis, setores, documentos, operacoes do GED sobre filesystem, uploads, lixeira, auditoria, middleware e comandos administrativos.

- `models/`: modelos separados por acesso, documentos, auditoria e lixeira; `__init__.py` preserva imports via `core.models`.
- `auth_views.py`: login, alteracao obrigatoria de senha, logout, health check e direcionamento inicial.
- `file_services.py`: segurança de caminhos, autorização física e validação de nomes compatíveis com Windows; mantém wrapper legado de upload.
- `file_queries.py`: listagem em cache e busca de diretórios do GED.
- `file_delivery.py`: validação, abertura, inferência de MIME e validação de URLs de retorno para arquivos entregues por HTTP.
- `navigation_views.py`: busca, navegação e paginação da interface do GED.
- `navigation_services.py`: configuração dos módulos e construção de breadcrumbs.
- `trash_services.py`: movimentação, exclusão múltipla, restauração e esvaziamento da lixeira, incluindo registro e auditoria.
- `trash_queries.py`: listagem, filtros e metadados dos itens da lixeira.
- `audit_queries.py`: consulta e filtros dos logs de auditoria.
- `storage_services.py`: política de upload múltiplo, persistência de uploads e criação segura de subpastas do GED.
- `storage_views.py`: endpoints HTTP de upload geral, upload múltiplo e criação de subpastas.
- `tests/test_uploads.py`: cobertura do validador de uploads, assinaturas de arquivos e persistência segura.
- `tests/test_filesystem.py`: cobertura de renomeação, autorização e ciclo da lixeira.
- `views.py`: fachada de compatibilidade e operacoes do GED ainda em migracao.
- `static/`: fontes estaticas compartilhadas; `staticfiles/` e somente saida gerada de `collectstatic`.

Dependencias externas principais: Django Auth, sessoes, filesystem local/rede e validacao de arquivos.

## Tramitacao

O app `tramitacao` gerencia o envio de documentos entre setores. Seu fluxo possui estados `PENDENTE`, `RECEBIDO`, `CONCLUIDO`, `DEVOLVIDO` e `ARQUIVADO`. O modelo principal e `Tramitacao`; historico e anexos preservam as movimentacoes.

- `services.py`: comandos e regras que alteram o fluxo.
- `models/`: modelos separados entre `workflow.py` e `attachments.py`; `__init__.py` preserva os imports públicos.
- `workflow.py`: transicoes de status e operacoes de recebimento, conclusao, devolucao e lote.
- `signatures.py`: assinatura eletronica e validacao de senha.
- `responses.py`: resposta, despacho, destinatarios, historico e anexos da resposta.
- `destinations.py`: resolucao e validacao de setor e funcionario de destino.
- `dispatch.py`: criacao, edicao, devolucao e reenvio de tramitacoes.
- `permissions.py`: acesso por usuario, setor e acao da tramitacao.
- `history.py`: montagem do historico e seus anexos para a interface/API.
- `attachments.py`: resolucao de campos, validacao e persistencia de anexos.
- `queries.py`: consultas de leitura reutilizaveis, incluindo contagem de notificacoes pendentes.
- `dispatch.py`: criacao, edicao, reenvio e exclusao de tramitacoes devolvidas.
- `views.py`: entrada HTTP e montagem de respostas.
- `forms/`: validacao de entrada separada entre `submission.py` e `response.py`; `__init__.py` preserva os imports publicos.
- `templates/tramitacao/`: apresentacao da caixa e modais.
- `templates/tramitacao/includes/`: componentes de template reutilizaveis, incluindo modais, abas de listagem e paginacao compartilhada.
- `templates/tramitacao/includes/aba_recebidos.html`: listagem e atualizacao HTMX dos recebidos.
- `templates/tramitacao/includes/aba_enviados.html`: listagem dos enviados.
- `templates/tramitacao/includes/aba_arquivados.html`: listagem dos arquivados.
- `templates/tramitacao/includes/paginacao.html`: controles comuns de paginacao por aba.
- `management/commands/`: tarefas operacionais de vencimento e limpeza.

As funcoes de consulta continuam reexportadas por `services.py` temporariamente para preservar imports existentes.

## Eventos

Imagens e certificados sao armazenados em subpastas por evento dentro de `EVENTOS_DIR`. Criacao, edicao, inscricao, presenca e emissao/envio de certificados usam a auditoria compartilhada.

## Ecarta

O app `ecarta` importa arquivos de endereco, gera e arquiva os arquivos de cada lote em `ECARTA_DIR` e disponibiliza downloads. A sessao continua guardando o resultado imediato para manter compatibilidade com o fluxo atual.

- `services.py`: leitura e normalizacao de CSV/XLS/XLSX, geracao e persistencia dos arquivos do lote; valida a planilha antes de consumir o lote e registra a acao na auditoria compartilhada.
- `models.py`: `LoteEcarta` guarda quem gerou o lote e os caminhos dos arquivos de servico/resposta em `ECARTA_DIR/lotes/<numero>/`.
- `views.py`: processamento HTTP, autenticacao, mensagens e sessao; preserva aliases dos downloads.
- `download_views.py`: downloads ZIP do arquivo de servico e da resposta.
- `tests.py`: testes de geração de lotes, downloads e contratos HTTP.

## Setup

O pacote `setup` configura Django, banco, middleware, logging, staticfiles, media e URLs raiz. A separacao futura de settings deve manter `setup.settings` como compatibilidade durante a transicao.

## Dependencias entre apps

```text
setup -> core
setup -> tramitacao -> core
setup -> ecarta -> core
```

`core` nao deve importar `tramitacao` ou `ecarta`. Isso evita ciclos e mantem os apps de dominio dependentes apenas das capacidades compartilhadas.

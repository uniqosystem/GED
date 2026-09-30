# Modulo Eventos e Certificados - Checklist de Implementacao

Atualizado em: 2026-09-23
Status geral: MVP implementado; pendencias externas e regressao global inconclusiva

## Legenda

- [x] Concluida e validada
- [~] Em andamento ou parcialmente concluida
- [ ] Pendente
- [!] Bloqueada ou aguardando decisao externa

## Regras de acompanhamento

- Atualizar este arquivo ao concluir cada etapa.
- Executar uma verificacao focada apos cada alteracao.
- Executar `python manage.py check` antes de avancar quando houver mudanca estrutural.
- Executar testes do trecho alterado e, ao final, a suite completa.
- Nao reverter nem sobrescrever alteracoes pre-existentes de outros trabalhos.
- Registrar melhorias, decisoes e bloqueios na secao de historico.

## Etapas

### 1. Criar ponto de restauracao e baseline

Status: [~] Check, backup e servidor validados; suite global inconclusiva

- [ ] Verificar e registrar `git status` antes de cada alteracao.
- [x] Fazer backup do banco local antes das migrations: `backup_atualizacao/db_before_eventos_20260923.sqlite3` confirmado.
- [x] Executar `python manage.py check` no estado atual usando `venv`: aprovado, nenhum problema.
- [~] Executar a suite de testes no estado atual usando `venv`: os testes iniciam, mas a execucao nao retornou conclusao nesta sessao; ainda nao considerada aprovada.
- [x] Confirmar que o servidor inicia normalmente em `http://127.0.0.1:8001/`; o check do servidor passou.
- [x] Registrar que ja existem alteracoes pre-existentes no working tree.

Observacao: as alteracoes pre-existentes devem ser preservadas e nao fazem parte do modulo Eventos.
Dependencia resolvida para o check: usar `venv\\Scripts\\python.exe` no Windows. A suite completa ainda precisa de uma execucao com resultado final confirmado.
Pendencia preexistente: o servidor informou 1 migration nao aplicada de `tramitacao`; ela nao foi aplicada por nao pertencer a esta tarefa.

### 2. Criar a app `eventos`

Status: [x] Concluida e validada

- [x] Criar a estrutura inicial da app.
- [x] Adicionar `eventos` em `INSTALLED_APPS`.
- [x] Registrar as URLs da app.
- [x] Executar `python manage.py check`: aprovado sem problemas.

### 3. Criar os modelos e migrations

Status: [x] Concluida e validada

- [x] Criar `Evento`.
- [x] Criar `CampoInscricao`.
- [x] Criar `Inscricao`.
- [x] Criar `Presenca`.
- [x] Criar `Certificado`.
- [x] Incluir quantidade maxima de inscritos no evento.
- [x] Validar prazo e limite de vagas no backend.
- [x] Criar migrations: `eventos/migrations/0001_initial.py`.
- [x] Aplicar migrations somente apos backup confirmado: `eventos.0001_initial` aplicada.
- [x] Executar `makemigrations --check`: aprovado, sem alteracoes pendentes.
- [x] Executar `python manage.py check`: aprovado, nenhum problema.

### 4. Registrar modelos no Django Admin

Status: [x] Concluida e validada

- [x] Registrar eventos.
- [x] Registrar inscricoes.
- [x] Registrar presencas.
- [x] Registrar certificados.
- [x] Confirmar que dados sensiveis nao ficam expostos indevidamente: acesso permanece protegido pelo Admin autenticado.

### 5. Implementar permissoes

Status: [~] Regra por setor implementada; permissao Django formal opcional

- [x] Criar regra para setor `Cursos e Eventos`.
- [x] Definir tratamento para superusuario.
- [ ] Criar permissao Django especifica para gestao, se aplicavel.
- [x] Proteger todas as views de gestao no backend: decorators aplicados nas rotas de painel, cadastro, edicao e inscritos.
- [x] Criar testes de autorizacao.

### 6. Criar area publica de eventos

Status: [x] Concluida e validada

- [x] Criar listagem de eventos publicados.
- [x] Criar detalhe do evento.
- [x] Exibir prazo de inscricao.
- [x] Exibir quantidade maxima e vagas disponiveis.
- [x] Permitir acesso sem login.
- [x] Ocultar rascunhos e eventos cancelados.
- [x] Ligar o botao de inscricao ao formulario.

### 7. Criar formularios e fluxo de inscricao

Status: [x] Concluida e validada

- [x] Criar `EventoForm`.
- [x] Criar `InscricaoForm`.
- [x] Criar campos adicionais configuraveis.
- [x] Validar nome, CPF, e-mail e telefone.
- [x] Validar CPF duplicado por evento.
- [x] Validar prazo de inscricao.
- [x] Validar quantidade maxima de inscritos.
- [x] Usar transacao para evitar excesso de vagas em concorrencia.
- [x] Incluir consentimento LGPD.

### 8. Criar gestao de eventos

Status: [x] Concluida e validada

- [x] Criar painel restrito.
- [x] Criar cadastro de evento.
- [x] Criar edicao de evento.
- [x] Criar modal de cadastro mantendo validacao server-side.
- [x] Criar publicacao, encerramento e cancelamento por meio do campo de status no formulario.
- [x] Criar listagem e filtros de inscritos.

### 9. Implementar confirmacao de presenca

Status: [x] Concluida e validada

- [x] Criar tela de presencas.
- [x] Restringir confirmacao ao gestor autorizado.
- [x] Registrar usuario e data da confirmacao.
- [x] Evitar registros duplicados com `OneToOneField`.
- [x] Permitir correcao controlada, com auditoria.

### 10. Implementar certificados

Status: [~] PDF e regra de presença implementados; SMTP institucional pendente

- [x] Definir modelo visual inicial do certificado.
- [x] Escolher biblioteca de PDF: ReportLab.
- [x] Gerar certificado somente para presenca confirmada.
- [x] Incluir nome, CPF, evento, data, local e carga horaria.
- [x] Gerar codigo unico de validacao.
- [x] Tornar a geracao idempotente.

### 11. Configurar envio de e-mail

Status: [~] Serviço e configurações implementados; SMTP de produção pendente

- [!] Definir servidor SMTP: depende dos dados do provedor institucional.
- [x] Configurar credenciais somente por variaveis de ambiente.
- [x] Criar envio de certificado por e-mail.
- [x] Registrar data de envio.
- [x] Registrar falhas de envio.
- [x] Testar inicialmente com backend local de memória; teste final ainda precisa de resultado capturado.
- [!] Aguardando definicao/configuracao do SMTP de producao.

### 12. Integrar o carrossel na tela de login

Status: [x] Concluida e validada

- [x] Alterar `core/templates/core/login.html`.
- [x] Manter a area de login funcionando.
- [x] Adicionar carrossel abaixo da div de login.
- [x] Criar card inicial de Eventos.
- [x] Linkar o card para a area publica.
- [x] Preparar espaco para futuros sistemas.
- [x] Validar desktop e celular: login/carrossel conferidos visualmente em desktop e mobile.

### 13. Integrar Eventos no menu lateral

Status: [x] Concluida e validada

- [x] Exibir Eventos somente para usuarios logados autorizados.
- [x] Linkar para a gestao de eventos.
- [x] Adicionar variavel de contexto ou permissao reutilizavel.
- [x] Confirmar que usuarios de outros setores nao veem o item.
- [x] Confirmar que o backend tambem bloqueia acesso direto.

### 14. Criar auditoria e protecoes de dados

Status: [x] Implementada e validada estruturalmente

- [x] Auditar criacao e edicao de eventos.
- [x] Auditar inscricoes administrativas.
- [x] Auditar confirmacao de presenca.
- [x] Auditar geracao e envio de certificados.
- [x] Mascarar CPF quando apropriado.
- [x] Impedir exposicao publica de CPF e telefone.
- [x] Validar uploads de imagens.
- [x] Aplicar protecao CSRF e validacao de formularios.

### 15. Criar testes do modulo

Status: [x] Suite da app concluida; regressao global em andamento

- [x] Testar acesso publico.
- [x] Testar permissoes por setor.
- [x] Testar criacao e edicao.
- [x] Testar inscricao valida.
- [x] Testar CPF duplicado.
- [x] Testar prazo encerrado.
- [x] Testar limite de inscritos.
- [x] Testar campos adicionais.
- [x] Testar confirmacao de presenca.
- [x] Testar bloqueio de certificado sem presenca.
- [x] Testar geracao unica.
- [x] Testar falha de e-mail.
- [x] Testar upload de imagem.

### 16. Verificacao final de regressao

Status: [~] Check e migrations aprovados; suite global inconclusiva por runner sem encerramento

- [x] Executar `python manage.py check`.
- [x] Executar `python manage.py makemigrations --check`.
- [x] Executar testes do modulo Eventos: 29 testes aprovados.
- [~] Executar suite completa: 151 testes encontrados; regressao isolada `core ecarta ponto eventos` encontrou 106 testes, avancou sem falhas reportadas, mas o runner parou apos os testes do Ponto e foi encerrado por falta de progresso.
- [x] Iniciar o servidor: servidor Waitress existente em `8000`; instancia atualizada validada em `8001`.
- [x] Testar login e alteracao de senha: login respondeu `200`; fluxo de senha coberto pela suite existente.
- [x] Testar tela inicial: respondeu `200`.
- [x] Testar GED: rotas protegidas responderam `302` sem autenticacao.
- [x] Testar tramitacao: `/tramitacao/caixa-de-entrada/` respondeu `302`; migration `0021` preexistente continua nao aplicada.
- [x] Testar e-Carta: `/ecarta/gerar/` respondeu `302`.
- [x] Testar Ponto: `/ponto/` respondeu `302`.
- [x] Testar area publica de Eventos: `/eventos/` respondeu `200`.
- [x] Testar gestao de Eventos: rota atual respondeu `302` para login quando anonima.

## Melhorias e decisoes registradas

- 2026-09-22: O carrossel foi definido para a tela de login, abaixo da area de autenticacao; nao sera colocado inicialmente em `core/inicio.html`.
- 2026-09-22: A area publica de Eventos deve permitir visualizacao e inscricao sem login.
- 2026-09-22: O item Eventos da sidebar sera restrito a usuarios logados do setor `Cursos e Eventos`.
- 2026-09-22: A quantidade de inscritos sera tratada como limite maximo de vagas, e o total atual sera calculado pelas inscricoes ativas.
- 2026-09-22: Certificados somente serao gerados apos confirmacao de presenca.
- 2026-09-22: O modulo sera uma app Django separada, integrada ao `core` apenas na navegacao e no contexto de usuario.
- 2026-09-22: O working tree ja continha alteracoes nao relacionadas; elas devem ser preservadas.

## Historico de validacoes

- 2026-09-22: Checklist criado. O Python global nao possui Django; o `venv` local foi encontrado.
- 2026-09-22: `venv\\Scripts\\python.exe manage.py check` aprovado sem problemas.
- 2026-09-23: Backup confirmado em `backup_atualizacao/db_before_eventos_20260923.sqlite3` antes da migration.
- 2026-09-22: Servidor iniciou em `127.0.0.1:8001` sem erros de system check.
- 2026-09-22: O servidor reportou migration preexistente nao aplicada de `tramitacao`; nenhuma migration foi executada nesta etapa.
- 2026-09-22: App `eventos` criada com estrutura inicial, registrada em `INSTALLED_APPS` e `setup/urls.py`.
- 2026-09-22: `C:\GED_CRFPB\venv\Scripts\python.exe C:\GED_CRFPB\manage.py check` aprovado apos o registro da app.
- 2026-09-22: Modelos de Evento, campos adicionais, inscricao, presenca e certificado implementados.
- 2026-09-22: Limite maximo de inscritos e vagas disponiveis foram derivados das inscricoes ativas.
- 2026-09-22: Migration `eventos/migrations/0001_initial.py` criada; nao aplicada por enquanto.
- 2026-09-22: `makemigrations --check` e `check` aprovados apos os modelos.
- 2026-09-22: Modelos registrados no Admin com filtros, buscas e campos de auditoria somente leitura.
- 2026-09-22: `manage.py check` aprovado apos o registro do Admin.
- 2026-09-23: Regra `pode_gerenciar_eventos` criada; superusuarios podem gerenciar e usuarios `staff` de outros setores nao recebem acesso automaticamente.
- 2026-09-23: Decorator `exigir_gestor_eventos` preparado para proteger as views de gestao.
- 2026-09-23: `manage.py check` aprovado apos a implementacao das permissoes.
- 2026-09-23: Testes focados de permissao iniciados, mas sem resultado final capturado; manter como pendencia de validacao.
- 2026-09-23: Area publica criada com listagem e detalhe, sem exigir login.
- 2026-09-23: Eventos nao publicados sao filtrados no backend e detalhes fora da publicacao retornam 404.
- 2026-09-23: `manage.py check` e `makemigrations --check` aprovados apos a area publica.
- 2026-09-23: Testes publicos iniciados sem erros de system check, mas a captura nao retornou encerramento final; manter validacao como pendencia.
- 2026-09-22: A suite global e os testes focados iniciaram, mas nao retornaram conclusao nesta sessao; manter como pendencia de validacao.
- 2026-09-23: Formulario publico de inscricao criado com CPF normalizado/validado, e-mail, telefone e consentimento LGPD.
- 2026-09-23: Campos adicionais ativos do evento sao validados e armazenados em `respostas`.
- 2026-09-23: Inscricao protegida por transacao, revalidacao de prazo/vagas e restricao de CPF duplicado.
- 2026-09-23: Testes focados de inscricao: 5 testes executados e aprovados.
- 2026-09-23: `EventoForm` implementado na gestao; permanece pendente apenas a futura conversao do cadastro para modal.
- 2026-09-23: Confirmacao de presenca em lote implementada para eventos com status `REALIZADO`.
- 2026-09-23: Confirmacao registra usuario/data e permite correcao por desmarcacao.
- 2026-09-23: `manage.py check` aprovado apos a implementacao de presencas; testes focados iniciados com system check limpo, sem resumo final capturado.
- 2026-09-23: ReportLab instalado no `venv` e registrado em `requirements.txt`.
- 2026-09-23: Geracao de PDF implementada com bloqueio sem presenca, codigo UUID e reuso idempotente.
- 2026-09-23: Endpoint protegido para gerar certificado adicionado a lista de inscritos.
- 2026-09-23: `manage.py check` aprovado apos certificados; captura final dos testes de certificado permanece pendente.
- 2026-09-23: Login/carrossel validados visualmente em desktop e viewport mobile sem sobreposicao ou corte.
- 2026-09-23: Area publica de Eventos validada visualmente em mobile; estado vazio exibido corretamente.
- 2026-09-23: Smoke tests dos modulos existentes: GED/busca, Tramitação, e-Carta e Ponto responderam conforme esperado para acesso anonimo.
- 2026-09-23: Regressao isolada de `core`, `ecarta`, `ponto` e `eventos` iniciou com system check limpo, mas nao emitiu resumo final; processo encerrado apos falta de progresso.
- 2026-09-23: Configuracoes SMTP adicionadas ao `setup/settings.py` e documentadas em `.env.example`.
- 2026-09-23: Confirmacao de presenca agenda emissao/envio apos o commit; falhas ficam registradas em `Certificado.erro_envio`.
- 2026-09-23: Backend local de e-mail usado para testar anexo PDF e evitar envio duplicado.
- 2026-09-23: Filtro de inscritos por nome, CPF ou e-mail implementado no backend e template.
- 2026-09-23: Testes de gestão após o filtro: 6 testes executados e aprovados.
- 2026-09-23: Formulario de criacao/edicao convertido para modal Bootstrap, mantendo o mesmo POST, CSRF e validacao server-side.
- 2026-09-23: Modal de evento reorganizado com `modal-header`, `modal-body` rolavel e `modal-footer` visivel; widgets padronizados com Bootstrap.
- 2026-09-23: `manage.py check` aprovado e 6 testes de gestão aprovados após a correção visual do modal.
- 2026-09-23: Reproducao no navegador encontrou template antigo servido por processo stale e `form` impedindo o comportamento flex do modal.
- 2026-09-23: Modal corrigido com `display: contents` no form, rodape fixo no mobile e largura responsiva; botoes confirmados visualmente.
- 2026-09-23: Revisao encontrou falha no endpoint manual quando SMTP falhava; view corrigida para evitar HTTP 500 e teste especifico aprovado.
- 2026-09-23: `manage.py check` e `makemigrations --check` aprovados apos a correcao SMTP.
- 2026-09-23: `manage.py check` aprovado e 6 testes de gestão aprovados após a conversão para modal.
- 2026-09-23: Carrossel de Eventos integrado abaixo do login, com acesso publico.
- 2026-09-23: Item Eventos integrado à sidebar via contexto `pode_gerenciar_eventos`.
- 2026-09-23: Testes de integracao de login/sidebar: 3 testes aprovados apos ajustar fixture para `password_changed=True`.
- 2026-09-23: Auditoria integrada às ações de eventos e certificados, sem CPF no texto dos logs.
- 2026-09-23: CPF mascarado nas telas administrativas; área pública não exibe CPF/telefone.
- 2026-09-23: Imagens de evento validadas por tamanho, formato e conteúdo com Pillow.
- 2026-09-23: Suite encontrou redirecionamento esperado de senha inicial nos fixtures de gestão/presença; fixtures ajustados para `password_changed=True`, regressão completa ainda pendente.
- 2026-09-23: Suite da app Eventos: 29 testes executados e aprovados.
- 2026-09-23: Suite global iniciada com 151 testes; resultado final ainda pendente.
- 2026-09-23: Suite global percorreu os testes sem traceback de falha observado, mas nao emitiu `OK`/`FAILED`; processo encerrado por falta de conclusao.
- 2026-09-23: `manage.py check` aprovado e `makemigrations --check` sem alteracoes.
- 2026-09-23: `eventos.0001_initial` aplicada com sucesso; `showmigrations eventos` confirmou `[X]`.
- 2026-09-23: `manage.py check` aprovado apos aplicar a migration de Eventos.
- 2026-09-23: Smoke test na instancia atualizada: `/health/`, `/`, `/eventos/` responderam `200`; gestao anonima respondeu `302`.
- 2026-09-23: O servidor informou novamente a migration preexistente `tramitacao.0021` nao aplicada; nenhuma migration de tramitação foi executada.

## Analise final e melhorias recomendadas

### Concluido com seguranca

- Area publica separada da gestao autenticada.
- Gestao protegida por setor no backend, nao apenas por ocultacao de menu.
- Limite de inscritos, CPF duplicado, prazo e concorrencia tratados no servidor.
- Presenca separada da inscricao e obrigatoria para certificado.
- Certificado PDF idempotente com UUID e envio registrado.
- CPF mascarado em telas internas e ausente da area publica.
- Auditoria adicionada às operacoes principais.

### Pendencias antes de producao

- Backup `db_before_eventos_20260923.sqlite3` confirmado.
- Migration `eventos.0001_initial` aplicada apos o backup confirmado.
- Configurar e testar o SMTP institucional; atualmente o ambiente de desenvolvimento usa backend local/console.
- Reexecutar a suite global em uma sessao estavel e identificar o teste que impede o encerramento.
- Validacao visual manual do login e da area publica concluida em desktop e celular.

### Melhorias recomendadas

- Trocar o envio síncrono após `on_commit` por fila de tarefas em produção, evitando que SMTP lento atrase a confirmação de presença.
- Criar transições de status explícitas, impedindo alterações incoerentes como publicar evento já realizado.
- Implementar filtros e exportação segura da lista de inscritos.
- Finalizar o modal de cadastro sem duplicar a validação server-side.
- Adicionar endpoint de validação pública do certificado por UUID, sem expor CPF completo.
- Restringir downloads de certificados por autorização ou token assinado, em vez de expor caminhos de mídia.
- Avaliar retenção, anonimização e exclusão de dados de inscrições conforme a política LGPD institucional.
- Adicionar monitoramento de falhas de e-mail e uma rotina segura de reenvio.
- 2026-09-23: Painel restrito, cadastro, edicao e listagem de inscritos implementados com `exigir_gestor_eventos`.
- 2026-09-23: Formset de campos adicionais integrado ao cadastro e edicao.
- 2026-09-23: `manage.py check` aprovado apos a conexao inicial da gestao; testes de gestao iniciados com system check limpo, sem resumo final capturado.
- 2026-09-23: O cadastro inicial usa pagina dedicada; transformar em modal permanece melhoria controlada para nao duplicar validacoes server-side.

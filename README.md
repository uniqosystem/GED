# GED_CRFPB

Sistema de Gestao Eletrônica de Documentos do Conselho Regional de Farmacia da Paraiba (CRFPB).

## Visao geral

O projeto é uma aplicação Django com três apps principais:

- `core`: autenticação, perfis, acesso seguro ao filesystem, uploads, navegação, lixeira e auditoria.
- `tramitacao`: envio de documentos entre setores, respostas, devoluções, assinaturas e histórico.
- `ecarta`: leitura de planilhas e geração dos arquivos de lote e-Carta.

As responsabilidades estão organizadas em views, services, queries, modelos e testes por fluxo. Consulte [docs/architecture.md](docs/architecture.md) e [docs/modules.md](docs/modules.md) para detalhes.

## Requisitos

- Python 3.14 ou compativel.
- Django 6.0.6.
- Dependencias listadas em `requirements.txt`.
- Windows, quando o GED usar caminhos locais ou de rede.

## Instalacao

No PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copie `.env.example` para `.env` e configure pelo menos:

```text
SECRET_KEY=gere-uma-chave-secreta
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
GED_BASE_DIR=C:\GED
SETORES_BASE_DIR=C:\SETORES
LIXEIRA_DIR=C:\GED_LIXEIRA
TRAMITACAO_DIR=C:\TRAMITACAO
```

Os caminhos devem existir e ter as permissoes necessarias para o processo do servidor. Nunca publique `.env`, credenciais ou o banco local.

## Banco e verificacoes

```powershell
python manage.py migrate
python manage.py check
python manage.py test --verbosity 1
```

O ambiente de desenvolvimento foi validado com 108 testes aprovados e 1 ignorado.

## Execucao

Para desenvolvimento:

```powershell
python manage.py runserver
```

Para o servidor Waitress configurado no projeto:

```powershell
python run_server.py
```

As entradas WSGI e ASGI sao `setup.wsgi:application` e `setup.asgi:application`.

## Backups

Os scripts `backup_diario.bat` e `backup_mensal.bat` dependem de caminhos configurados no computador de produção. Antes de usa-los, confirme as raizes, a política de copia do SQLite e o comportamento de `/MIR`. Consulte [docs/operations/backups.md](docs/operations/backups.md).

## Seguranca

- Nao versionar `.env`, `db.sqlite3`, `venv`, caches ou arquivos compilados.
- Usar `DEBUG=False` fora do desenvolvimento.
- Configurar `SECRET_KEY`, `ALLOWED_HOSTS` e origens CSRF adequadamente.
- Confirmar permissoes de leitura e escrita nas raizes do GED antes do deploy.

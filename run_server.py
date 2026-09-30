import sys

from django.core.management import call_command
from django.core.management.base import CommandError
from waitress import serve
from setup.wsgi import application # Certifique-se que o caminho está correto

if __name__ == '__main__':
    try:
        call_command('seed_admin')
    except CommandError as erro:
        # Falha no seed não deve impedir o sistema de subir.
        print(f'AVISO: seed do admin não executado: {erro}', file=sys.stderr)
    print("Servidor rodando em http://ti-pc02:8000")
    serve(application, host='0.0.0.0', port=8000)

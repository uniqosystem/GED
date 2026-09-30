from django.core.management import call_command
from waitress import serve
from setup.wsgi import application # Certifique-se que o caminho está correto

if __name__ == '__main__':
    call_command('seed_admin')
    print("Servidor rodando em http://ti-pc02:8000")
    serve(application, host='0.0.0.0', port=8000)

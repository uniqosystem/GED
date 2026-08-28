from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Cria grupos de acesso PF/PJ e atribui usuários explicitamente informados.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pf-users',
            default='',
            help='Usuários separados por vírgula para o grupo de Pessoa Física.',
        )
        parser.add_argument(
            '--pj-users',
            default='',
            help='Usuários separados por vírgula para o grupo de Pessoa Jurídica.',
        )

    def handle(self, *args, **options):
        grupos = {
            'PF': self._nomes_configurados('GED_PF_GROUPS'),
            'PJ': self._nomes_configurados('GED_PJ_GROUPS'),
        }
        usuarios = {
            'PF': self._nomes_usuarios(options['pf_users']),
            'PJ': self._nomes_usuarios(options['pj_users']),
        }

        for tipo, nomes_grupo in grupos.items():
            for nome_grupo in nomes_grupo:
                grupo, criado = Group.objects.get_or_create(name=nome_grupo)
                acao = 'Criado' if criado else 'Já existente'
                self.stdout.write(f'{acao}: grupo {nome_grupo}')
                self._atribuir_usuarios(grupo, usuarios[tipo])

    @staticmethod
    def _nomes_configurados(nome_setting):
        nomes = getattr(settings, nome_setting, [])
        if not nomes:
            raise CommandError(f'Nenhum grupo configurado em {nome_setting}.')
        return nomes

    def _nomes_usuarios(self, valor):
        return [nome.strip() for nome in valor.split(',') if nome.strip()]

    def _atribuir_usuarios(self, grupo, nomes_usuarios):
        for nome_usuario in nomes_usuarios:
            usuario = User.objects.filter(username=nome_usuario).first()
            if not usuario:
                self.stderr.write(f'Usuário não encontrado: {nome_usuario}')
                continue
            grupo.user_set.add(usuario)
            self.stdout.write(f'Usuário {nome_usuario} atribuído a {grupo.name}')

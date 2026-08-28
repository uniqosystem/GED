import os

from django.conf import settings
from django.core.management.base import BaseCommand

from tramitacao.models import AnexoHistorico, AnexoTramitacao


class Command(BaseCommand):
    help = 'Lista ou remove arquivos de anexos sem referência no banco.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Remove os arquivos órfãos encontrados.',
        )

    def handle(self, *args, **options):
        raiz = os.path.abspath(os.path.join(settings.MEDIA_ROOT, 'tramitacoes'))
        if not os.path.isdir(raiz):
            self.stdout.write('Diretório de anexos não encontrado; nada a fazer.')
            return

        referenciados = {
            self._normalizar_nome(nome)
            for nome in AnexoTramitacao.objects.values_list('arquivo', flat=True)
        }
        referenciados.update(
            self._normalizar_nome(nome)
            for nome in AnexoHistorico.objects.values_list('arquivo', flat=True)
        )

        orfaos = []
        for diretorio, _, arquivos in os.walk(raiz):
            for nome in arquivos:
                caminho = os.path.join(diretorio, nome)
                nome_relativo = self._normalizar_nome(os.path.relpath(caminho, settings.MEDIA_ROOT))
                if nome_relativo not in referenciados:
                    orfaos.append(caminho)

        aplicar = options['apply']
        for caminho in orfaos:
            if aplicar:
                try:
                    os.remove(caminho)
                except OSError as exc:
                    self.stderr.write(f'Falha ao remover {caminho}: {exc}')
            else:
                self.stdout.write(f'[dry-run] {caminho}')

        acao = 'removido(s)' if aplicar else 'encontrado(s)'
        self.stdout.write(self.style.SUCCESS(f'{len(orfaos)} arquivo(s) órfão(s) {acao}.'))

    @staticmethod
    def _normalizar_nome(nome):
        return str(nome).replace('\\', '/').lstrip('./').casefold()

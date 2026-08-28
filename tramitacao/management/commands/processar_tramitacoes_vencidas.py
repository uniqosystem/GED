from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import LogAuditoria
from tramitacao.models import HistoricoTramitacao, Tramitacao


class Command(BaseCommand):
    help = 'Devolve tramitações pendentes vencidas para o setor de origem.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Lista as tramitações vencidas sem alterar o banco.',
        )

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        dry_run = options['dry_run']
        ids = list(
            Tramitacao.objects.filter(
                data_limite_resposta__lt=hoje,
                status='PENDENTE',
                auto_devolvido=False,
            ).values_list('id', flat=True)
        )

        processadas = 0
        ignoradas = 0

        for tramitacao_id in ids:
            with transaction.atomic():
                tramitacao = (
                    Tramitacao.objects.select_for_update()
                    .select_related('remetente', 'setor_origem', 'setor_destino')
                    .filter(pk=tramitacao_id)
                    .first()
                )

                if not tramitacao or tramitacao.status != 'PENDENTE' or tramitacao.auto_devolvido:
                    ignoradas += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f'[dry-run] Protocolo {tramitacao.protocolo} '
                        f'(prazo {tramitacao.data_limite_resposta:%d/%m/%Y})'
                    )
                    processadas += 1
                    continue

                setor_destino_anterior = tramitacao.setor_destino
                setor_origem_anterior = tramitacao.setor_origem

                HistoricoTramitacao.objects.create(
                    tramitacao=tramitacao,
                    remetente=tramitacao.remetente,
                    setor_origem=setor_origem_anterior,
                    despacho=(
                        'Documento devolvido automaticamente por decurso de prazo '
                        f'(Data limite: {tramitacao.data_limite_resposta:%d/%m/%Y}).'
                    ),
                    aguardar_resposta=tramitacao.aguardar_resposta,
                )

                tramitacao.setor_destino = setor_origem_anterior
                tramitacao.setor_origem = setor_destino_anterior
                tramitacao.usuario_destino = tramitacao.remetente
                tramitacao.status = 'RECEBIDO'
                tramitacao.auto_devolvido = True
                tramitacao.despacho = 'Retornado automaticamente: Prazo expirado.'
                tramitacao.save(update_fields=[
                    'setor_destino',
                    'setor_origem',
                    'usuario_destino',
                    'status',
                    'auto_devolvido',
                    'despacho',
                ])

                LogAuditoria.objects.create(
                    usuario=tramitacao.remetente,
                    acao='DEVOLVER_TRAMITACAO',
                    descricao=(
                        f'Devolveu automaticamente a tramitação de Protocolo: '
                        f'{tramitacao.protocolo} por decurso de prazo.'
                    ),
                    caminho_item=f'Retornado para o setor: {tramitacao.setor_destino}',
                )
                processadas += 1

        prefixo = '[dry-run] ' if dry_run else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'{prefixo}{processadas} tramitação(ões) processada(s); '
                f'{ignoradas} ignorada(s).'
            )
        )

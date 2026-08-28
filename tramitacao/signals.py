import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import AnexoHistorico, AnexoTramitacao

logger = logging.getLogger(__name__)


def remover_arquivo_se_orfao(anexo, modelo):
    nome_arquivo = anexo.arquivo.name
    if not nome_arquivo:
        return

    ainda_referenciado = modelo.objects.filter(arquivo=nome_arquivo).exists()
    outro_modelo = AnexoHistorico if modelo is AnexoTramitacao else AnexoTramitacao
    ainda_referenciado = ainda_referenciado or outro_modelo.objects.filter(arquivo=nome_arquivo).exists()
    if ainda_referenciado:
        return

    try:
        anexo.arquivo.storage.delete(nome_arquivo)
    except OSError:
        logger.exception('Falha ao remover anexo órfão: %s', nome_arquivo)


@receiver(post_delete, sender=AnexoTramitacao)
def remover_arquivo_anexo_tramitacao(sender, instance, **kwargs):
    remover_arquivo_se_orfao(instance, AnexoTramitacao)


@receiver(post_delete, sender=AnexoHistorico)
def remover_arquivo_anexo_historico(sender, instance, **kwargs):
    remover_arquivo_se_orfao(instance, AnexoHistorico)

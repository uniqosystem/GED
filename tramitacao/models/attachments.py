import os

from django.db import models
from django.utils import timezone

from .workflow import HistoricoTramitacao, Tramitacao


def caminho_upload_tramitacao(instance, filename):
    data_pasta = timezone.now().strftime('%d_%m_%Y')
    protocolo = instance.tramitacao.protocolo if hasattr(instance, 'tramitacao') and instance.tramitacao else 'geral'
    return os.path.join('tramitacoes', data_pasta, protocolo, filename)


class AnexoTramitacao(models.Model):
    tramitacao = models.ForeignKey(Tramitacao, on_delete=models.CASCADE, related_name='anexos')
    historico = models.ForeignKey(HistoricoTramitacao, on_delete=models.CASCADE, related_name='anexos', null=True, blank=True)
    arquivo = models.FileField(upload_to=caminho_upload_tramitacao)
    data_upload = models.DateTimeField(auto_now_add=True)


class AnexoHistorico(models.Model):
    historico = models.ForeignKey(HistoricoTramitacao, on_delete=models.CASCADE, null=True, blank=True)
    arquivo = models.FileField(upload_to=caminho_upload_tramitacao)
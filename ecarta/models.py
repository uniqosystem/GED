from django.db import models
from django.contrib.auth.models import User
from core.configured_storage import ConfiguredRootStorage

ecarta_storage = ConfiguredRootStorage('ECARTA_DIR')


def caminho_arquivo_lote(instance, filename):
    return f'lotes/{instance.numero_lote}/{filename}'


class ConfiguracaoEcarta(models.Model):
    ultimo_lote = models.IntegerField(default=0)

    def __str__(self):
        return f"Lote atual: {self.ultimo_lote}"


class LoteEcarta(models.Model):
    numero_lote = models.CharField(max_length=30, unique=True)
    criado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='lotes_ecarta')
    arquivo_servico = models.FileField(storage=ecarta_storage, upload_to=caminho_arquivo_lote)
    arquivo_resposta = models.FileField(storage=ecarta_storage, upload_to=caminho_arquivo_lote)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Lote e-Carta'
        verbose_name_plural = 'Lotes e-Carta'

    def __str__(self):
        return f'Lote e-Carta {self.numero_lote}'
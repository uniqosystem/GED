from django.contrib.auth.models import User
from django.db import models

from .access import Setor


class Prontuario(models.Model):
    TIPO_CHOICES = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
    ]
    numero_crf = models.CharField(max_length=20, unique=True, verbose_name='Número do CRF')
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES, verbose_name='Tipo de Inscrição')
    caminho_pasta = models.CharField(max_length=255, verbose_name='Caminho da Pasta')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Prontuário'
        verbose_name_plural = 'Prontuários'

    def __str__(self):
        return f'CRF {self.numero_crf} ({self.get_tipo_display()})'


class Documento(models.Model):
    nome_arquivo = models.CharField(max_length=255, verbose_name='Nome do Arquivo')
    caminho_arquivo = models.CharField(max_length=255, verbose_name='Caminho do Arquivo')
    tamanho_bytes = models.BigIntegerField(null=True, blank=True, verbose_name='Tamanho (Bytes)')
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE, null=True, blank=True, related_name='documentos')
    prontuario = models.ForeignKey(Prontuario, on_delete=models.CASCADE, null=True, blank=True, related_name='documentos')
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Inserido por')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Data de Inclusão')

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'

    def __str__(self):
        return self.nome_arquivo

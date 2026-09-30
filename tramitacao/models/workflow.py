from django.contrib.auth.models import User
from django.db import IntegrityError, OperationalError, models, transaction
from django.utils import timezone

from core.models import Documento, Setor


class Tramitacao(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('OFICIO', 'Ofício'),
        ('MEMORANDO', 'Memorando'),
        ('CIRCULAR', 'Circular'),
        ('REQUERIMENTO', 'Requerimento'),
        ('PROCESSO', 'Processo'),
        ('OUTROS', 'Outros'),
    ]
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('RECEBIDO', 'Recebido'),
        ('CONCLUIDO', 'Concluído'),
        ('DEVOLVIDO', 'Devolvido'),
        ('ARQUIVADO', 'Arquivado'),
    ]

    protocolo = models.CharField(max_length=50, unique=True, verbose_name="Número do Protocolo", db_index=True)
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Documento GED")
    criador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tramitacoes_criadas')
    setor_criador = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, related_name='tramitacoes_setor_criador')
    remetente_original = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tramitacoes_enviadas_original')
    setor_origem_original = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True, related_name='tramitacoes_setor_origem_original')
    remetente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tramitacoes_enviadas')
    setor_origem = models.ForeignKey(Setor, on_delete=models.CASCADE, related_name='setor_origem')
    setor_destino = models.ForeignKey(Setor, on_delete=models.CASCADE, related_name='setor_destino')
    usuario_destino = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuario_destino')
    tipo_documento = models.CharField(max_length=100, choices=TIPO_DOCUMENTO_CHOICES, default='OUTROS', verbose_name="Tipo de Documento")
    titulo = models.CharField(max_length=255, verbose_name="Título")
    despacho = models.TextField(verbose_name="Despacho")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observações")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    aguardar_resposta = models.BooleanField(default=False)
    data_limite_resposta = models.DateField(blank=True, null=True)
    data_envio = models.DateTimeField(auto_now_add=True)
    data_recebimento = models.DateTimeField(blank=True, null=True)
    auto_devolvido = models.BooleanField(default=False)
    exige_assinatura = models.BooleanField(default=False)
    assinado = models.BooleanField(default=False)
    data_assinatura = models.DateTimeField(null=True, blank=True)
    assinado_por = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='tramitacoes_assinadas')

    class Meta:
        verbose_name = "Tramitação"
        verbose_name_plural = "Tramitações"
        ordering = ['-data_envio']

    def save(self, *args, **kwargs):
        if self.pk or self.protocolo:
            return super().save(*args, **kwargs)

        for tentativa in range(3):
            try:
                with transaction.atomic():
                    hoje = timezone.now()
                    data_prefixo = hoje.strftime('%Y%m%d')
                    ultima = Tramitacao.objects.select_for_update().filter(
                        protocolo__startswith=data_prefixo
                    ).order_by('-protocolo').first()
                    novo_seq = int(ultima.protocolo[-4:]) + 1 if ultima else 1
                    self.protocolo = f"{data_prefixo}{novo_seq:04d}"
                    return super().save(*args, **kwargs)
            except (IntegrityError, OperationalError):
                self.protocolo = ''
                if tentativa == 2:
                    raise

    def __str__(self):
        return f"Protocolo: {self.protocolo} - {self.tipo_documento}"


class AssinaturaTramitacao(models.Model):
    tramitacao = models.ForeignKey(Tramitacao, on_delete=models.CASCADE, related_name='assinaturas')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assinaturas_tramitacoes')
    assinado = models.BooleanField(default=False)
    data_assinatura = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['data_assinatura', 'id']
        constraints = [
            models.UniqueConstraint(fields=['tramitacao', 'usuario'], name='assinatura_unica_por_usuario'),
        ]


class HistoricoTramitacao(models.Model):
    tramitacao = models.ForeignKey(Tramitacao, on_delete=models.CASCADE, related_name='historicos')
    remetente = models.ForeignKey(User, on_delete=models.CASCADE)
    setor_origem = models.ForeignKey(Setor, on_delete=models.CASCADE)
    despacho = models.TextField()
    aguardar_resposta = models.BooleanField(default=False)
    data_envio = models.DateTimeField(auto_now_add=True)
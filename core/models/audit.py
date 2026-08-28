from django.contrib.auth.models import User
from django.db import models


class LogAuditoria(models.Model):
    ACOES_CHOICES = [
        ('UPLOAD', 'Upload de Arquivo'),
        ('CRIAR_PASTA', 'Criação de Subpasta'),
        ('RENOMEAR', 'Renomear Item'),
        ('APAGAR', 'Mover para Lixeira'),
        ('CRIAR_TRAMITACAO', 'Nova Tramitação'),
        ('EDITAR_TRAMITACAO', 'Edição de Tramitação'),
        ('RESPONDER_TRAMITACAO', 'Resposta de Tramitação'),
        ('RECEBER_TRAMITACAO', 'Recebimento'),
        ('DEVOLVER_TRAMITACAO', 'Devolução'),
        ('CONCLUIR_TRAMITACAO', 'Conclusão'),
        ('ARQUIVAR_TRAMITACAO', 'Arquivamento'),
        ('EXCLUIR_TRAMITACAO', 'Exclusão de Tramitação'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_index=True)
    acao = models.CharField(max_length=50, db_index=True)
    data_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    descricao = models.CharField(max_length=255)
    caminho_item = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-data_hora']

    def __str__(self):
        user_str = self.usuario.username if self.usuario else 'Sistema'
        return f'{user_str} - {self.get_acao_display()} ({self.data_hora.strftime("%d/%m/%Y %H:%M")})'

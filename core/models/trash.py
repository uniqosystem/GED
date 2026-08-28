from django.contrib.auth.models import User
from django.db import models


class RegistroLixeira(models.Model):
    nome_na_lixeira = models.CharField(max_length=255)
    caminho_original = models.CharField(max_length=1024)
    data_exclusao = models.DateTimeField(auto_now_add=True)
    apagado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = 'Registro de Lixeira'

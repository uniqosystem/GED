from django.contrib.auth.models import User
from django.db import models


class Setor(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name='Nome do Setor')
    caminho_rede = models.CharField(max_length=255, verbose_name='Caminho na Rede (UNC)')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Setor'
        verbose_name_plural = 'Setores'

    def __str__(self):
        return self.nome


class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    setor = models.ForeignKey(Setor, on_delete=models.SET_NULL, null=True, blank=True)
    password_changed = models.BooleanField(default=False, verbose_name='Senha foi alterada no primeiro acesso')
    password_change_date = models.DateTimeField(null=True, blank=True, verbose_name='Data/Hora da alteração de senha')

    def __str__(self):
        return f'{self.user.username} - {self.setor}'

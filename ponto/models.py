import os 

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError

from .utils import calcular_distancia, CRFPB_LAT, CRFPB_LON

class RegistroPonto(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada (Início da Jornada)'),
        ('ALMOCO_SAIDA', 'Saída para Almoço'),
        ('ALMOCO_RETORNO', 'Retorno do Almoço'),
        ('SAIDA', 'Saída (Fim da Jornada)'),
    ]

    # Vincula o ponto ao usuário logado no Django
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Funcionário")
    
    # Registra a data e hora exata do batimento automaticamente
    data_hora = models.DateTimeField(default=timezone.now, verbose_name="Data/Hora do Registro")
    
    # Armazena o tipo de ponto selecionado
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Registro")
    
    # Campos para armazenar a geolocalização capturada pelo GPS do celular/PC
    latitude = models.FloatField(null=True, blank=True, verbose_name="Latitude")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Longitude")

    class Meta:
        verbose_name = "Registro de Ponto"
        verbose_name_plural = "Registros de Ponto"
        ordering = ['-data_hora'] # Mostra sempre os mais recentes primeiro

    def clean(self):
        # Valida apenas se os dados de localização estiverem presentes
        if self.latitude and self.longitude:
            distancia = calcular_distancia(self.latitude, self.longitude, CRFPB_LAT, CRFPB_LON)
            if distancia > 100:
                raise ValidationError(f"O registro está fora do raio permitido! (Distância: {int(distancia)}m)")

    def save(self, *args, **kwargs):
        self.full_clean()  # Força a validação antes de salvar
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_display()} em {self.data_hora.strftime('%d/%m/%Y %H:%M:%S')}"
    
class Ocorrencia(models.Model):
    TIPOS = [
        ('FERIAS', 'Férias'),
        ('ATESTADO', 'Atestado Médico'),
        ('LICENCA', 'Licença'),
        ('FALTA_JUST', 'Falta Justificada')
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ocorrencias')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    observacao = models.TextField(blank=True, null=True)
    anexo = models.FileField(upload_to='atestados/%Y/%m/%d/', null=True, blank=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.tipo} ({self.data_inicio} a {self.data_fim})"

class PerfilFuncionario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    horario_entrada = models.TimeField(default="08:00")
    horario_saida = models.TimeField(default="17:00")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    status = models.CharField(max_length=20, default="Ativo", choices=[
        ('Ativo', 'Ativo'),
        ('Ferias', 'Férias'),
        ('Atestado', 'Atestado'),
        ('Falta', 'Falta Justificada')
    ])

    def __str__(self):
        return f"{self.user.username} - {self.cpf}"
    
def path_contracheque(instance, filename):
    data = timezone.now()
    return f'contracheques/{data.year}/{data.month:02d}/{filename}'

class Contracheque(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    arquivo = models.FileField(upload_to=path_contracheque)
    mes = models.IntegerField()
    ano = models.IntegerField()
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.mes}/{self.ano}"
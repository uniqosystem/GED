from django.db import models


class ConfiguracaoEcarta(models.Model):
    ultimo_lote = models.IntegerField(default=0)

    def __str__(self):
        return f"Lote atual: {self.ultimo_lote}"
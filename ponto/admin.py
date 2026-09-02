from django.contrib import admin
from .models import RegistroPonto

@admin.register(RegistroPonto)
class RegistroPontoAdmin(admin.ModelAdmin):
    # Isso define quais colunas aparecerão na listagem do painel
    list_display = ('usuario', 'tipo', 'data_hora', 'latitude', 'longitude')
    # Isso adiciona um filtro na lateral direita para facilitar a busca
    list_filter = ('tipo', 'data_hora')
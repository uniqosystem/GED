import os
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from .models import RegistroLixeira


def listar_itens_lixeira(filtro_nome='', filtro_tipo=''):
    os.makedirs(settings.LIXEIRA_DIR, exist_ok=True)
    itens = os.listdir(settings.LIXEIRA_DIR)
    registros = {
        registro.nome_na_lixeira.casefold(): registro
        for registro in RegistroLixeira.objects.filter(nome_na_lixeira__in=itens).select_related('apagado_por')
    }
    arquivos = []
    for item in itens:
        caminho = os.path.join(settings.LIXEIRA_DIR, item)
        tipo = 'Arquivo' if os.path.isfile(caminho) else 'Pasta'
        if filtro_tipo and filtro_tipo != tipo or filtro_nome and filtro_nome not in item.lower():
            continue
        try:
            tamanho_num = os.path.getsize(caminho) if os.path.isfile(caminho) else sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(caminho) for filename in filenames
            )
            tamanho = f'{round(tamanho_num / 1024, 2)} KB'
        except OSError:
            tamanho = 'Indisponível'
        registro = registros.get(item.casefold())
        arquivos.append({
            'nome': item, 'tipo': tipo, 'tamanho': tamanho, 'caminho': caminho,
            'apagado_por': registro.apagado_por.username if registro and registro.apagado_por else 'Desconhecido',
            'data_exclusao': registro.data_exclusao if registro else None,
        })
    data_minima = timezone.make_aware(datetime.min) if settings.USE_TZ else datetime.min
    arquivos.sort(key=lambda item: item['data_exclusao'] or data_minima, reverse=True)
    return arquivos
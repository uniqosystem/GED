import os

from django.conf import settings


CONFIGURACOES_MODULO = {
    'pessoa-fisica': {
        'titulo': 'Pessoa Física',
        'subpasta_raiz': 'PESSOA FISICA',
    },
    'pessoa-juridica': {
        'titulo': 'Pessoa Jurídica',
        'subpasta_raiz': 'PESSOA JURIDICA',
    },
    'setores': {
        'titulo': 'Setores',
        'raiz_configuracao': 'SETORES_BASE_DIR',
    },
}


def por_pagina_seguro(valor, padrao):
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        return padrao
    return max(1, valor)


def obter_configuracao_modulo(modulo):
    configuracao = CONFIGURACOES_MODULO.get(modulo)
    if not configuracao:
        return None
    raiz = getattr(settings, configuracao.get('raiz_configuracao', 'GED_BASE_DIR'))
    if configuracao.get('subpasta_raiz'):
        raiz = os.path.join(raiz, configuracao['subpasta_raiz'])
    return {'raiz': raiz, 'titulo': configuracao['titulo']}


def construir_breadcrumbs(raiz_modulo, caminho_atual):
    relativo = os.path.relpath(caminho_atual, raiz_modulo)
    partes_pasta = []
    if relativo != '.':
        acumulado = raiz_modulo
        for parte in relativo.split(os.sep):
            acumulado = os.path.join(acumulado, parte)
            partes_pasta.append({'nome': parte, 'caminho': acumulado})
    pasta_pai = os.path.dirname(caminho_atual) if caminho_atual != raiz_modulo else None
    return partes_pasta, pasta_pai
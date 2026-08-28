import logging
import os
import urllib.parse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect

from .file_queries import listar_itens_diretorio, realizar_busca_diretorio
from .file_services import validar_acesso_ged, validar_caminho_seguro
from .navigation_services import construir_breadcrumbs, obter_configuracao_modulo, por_pagina_seguro
logger = logging.getLogger(__name__)


@login_required
def busca_crf(request):
    termo_busca = request.GET.get('crf', '').strip()
    ordem = request.GET.get('ordem', 'az')
    por_pagina = por_pagina_seguro(request.GET.get('por_pagina', 25), 25)
    pagina = request.GET.get('page', 1)
    resultados_totais = []

    if termo_busca:
        resultados_totais.extend(realizar_busca_diretorio(termo_busca, 'pessoa-fisica', request.user))
        resultados_totais.extend(realizar_busca_diretorio(termo_busca, 'pessoa-juridica', request.user))

    resultados_totais.sort(key=lambda item: item['nome'].lower(), reverse=(ordem == 'za'))
    resultados_paginados = Paginator(resultados_totais, por_pagina).get_page(pagina)

    return render(request, 'core/busca.html', {
        'resultados': resultados_paginados,
        'termo_busca': termo_busca,
        'ordem': ordem,
        'por_pagina': por_pagina,
        'pasta_encontrada': bool(resultados_totais),
    })


@login_required
@csrf_protect
def navegar_pastas(request, modulo):
    config = obter_configuracao_modulo(modulo)
    if not config:
        raise Http404('Módulo inválido.')

    raiz_modulo = config['raiz']
    caminho_subpasta = request.GET.get('pasta', '').strip()
    caminho_atual = urllib.parse.unquote(caminho_subpasta) if caminho_subpasta else raiz_modulo
    caminho_atual = validar_caminho_seguro(caminho_atual)
    validar_acesso_ged(request.user, caminho_atual, permitir_raiz_setores=True)
    try:
        caminho_no_modulo = os.path.commonpath([
            os.path.normcase(caminho_atual),
            os.path.normcase(raiz_modulo),
        ]) == os.path.normcase(raiz_modulo)
    except ValueError:
        caminho_no_modulo = False
    if not caminho_no_modulo:
        caminho_atual = raiz_modulo

    busca_interna = request.GET.get('busca_interna', '').strip()
    if busca_interna:
        itens = realizar_busca_diretorio(busca_interna, modulo, request.user)
    else:
        try:
            modulo_listagem = (
                'setores-raiz'
                if os.path.normpath(caminho_atual) == os.path.normpath(raiz_modulo)
                else modulo
            )
            itens = listar_itens_diretorio(caminho_atual, modulo_listagem, request.user)
        except (PermissionError, OSError):
            logger.exception('Falha ao listar diretório do GED')
            messages.error(request, 'Não foi possível acessar esta pasta.')
            itens = []

    ordem = request.GET.get('ordem', 'az')
    itens.sort(key=lambda item: item['nome'].lower(), reverse=(ordem == 'za'))
    pagina_atual = Paginator(
        itens,
        por_pagina_seguro(request.GET.get('por_pagina', 50), 50),
    ).get_page(request.GET.get('page', 1))

    partes_pasta, pasta_pai = construir_breadcrumbs(raiz_modulo, caminho_atual)
    contexto = {
        'modulo': modulo,
        'titulo': f"{config['titulo']} - {os.path.basename(caminho_atual) if caminho_atual != raiz_modulo else 'Raiz'}",
        'resultados': pagina_atual,
        'caminho_pasta_atual': caminho_atual,
        'partes_pasta': partes_pasta,
        'busca_interna': busca_interna,
        'pasta_pai': pasta_pai,
    }
    return render(request, 'core/navegar.html', contexto)

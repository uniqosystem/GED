import logging
import os
import urllib.parse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .file_delivery import abrir_arquivo_autorizado, tipo_conteudo_arquivo, url_retorno_segura
from .rename_service import renomear_item as renomear_item_service

logger = logging.getLogger(__name__)


@login_required
@xframe_options_sameorigin
def visualizar_arquivo(request):
    caminho_usuario = request.GET.get('caminho', '')
    try:
        arquivo, caminho_seguro = abrir_arquivo_autorizado(request.user, caminho_usuario)
    except Exception:
        logger.exception('Falha ao validar arquivo para visualização')
        return HttpResponse('Acesso negado.', status=403)

    response = FileResponse(arquivo, content_type=tipo_conteudo_arquivo(caminho_seguro))
    response['Content-Disposition'] = 'inline; filename="%s"' % os.path.basename(caminho_seguro)
    return response


@login_required
def baixar_arquivo(request):
    caminho_completo = request.GET.get('caminho', '')
    caminho_final = urllib.parse.unquote(caminho_completo)
    try:
        arquivo, _ = abrir_arquivo_autorizado(request.user, caminho_final)
    except FileNotFoundError as exc:
        raise Http404('Arquivo não encontrado.') from exc
    return FileResponse(arquivo, as_attachment=True)


@login_required
@require_POST
def renomear_arquivo(request):
    caminho_atual = request.POST.get('caminho_atual', '')
    crf = request.POST.get('crf', '')
    try:
        renomeado, conflito = renomear_item_service(
            request.user,
            caminho_atual,
            request.POST.get('novo_nome', ''),
        )
        if conflito:
            messages.error(request, 'Já existe um arquivo com esse nome.')
        elif renomeado:
            messages.success(request, 'Renomeado com sucesso!')
    except OSError:
        logger.exception('Falha ao renomear item do GED')
        messages.error(request, 'Não foi possível renomear o item.')

    if crf == 'bypass':
        return redirect(url_retorno_segura(request, request.GET.get('next'), '/inicio/'))
    return redirect(f'/busca/?crf={crf}')

import json
import logging
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .file_services import validar_acesso_ged, validar_caminho_seguro
from .file_views import url_retorno_segura
from .models import RegistroLixeira
from .trash_queries import listar_itens_lixeira
from .trash_services import (
    esvaziar_lixeira as executar_esvaziamento_lixeira,
    excluir_itens_lixeira,
    mover_para_lixeira,
    restaurar_item_lixeira,
)

logger = logging.getLogger(__name__)


def _is_superuser(user):
    return user.is_superuser


@login_required
@require_POST
def apagar_arquivo(request):
    caminho_atual = request.POST.get('caminho_atual', '').strip()
    crf = request.POST.get('crf', '').strip()
    sucesso, nome_item = mover_para_lixeira(request.user, caminho_atual)

    if sucesso:
        messages.success(request, f"Item '{nome_item}' movido para a lixeira!")
    else:
        messages.error(request, 'Erro ao mover o item após tentativas: falha de acesso ao arquivo')

    if crf == 'bypass':
        return redirect(url_retorno_segura(request, request.GET.get('next'), '/inicio/'))
    return redirect(f'/busca/?crf={crf}')


@login_required
@csrf_protect
@require_POST
def excluir_multiplos_ajax(request):
    try:
        itens = json.loads(request.body).get('itens', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Dados JSON inválidos.'}, status=400)
    if not itens:
        return JsonResponse({'error': 'Nenhum item foi selecionado.'}, status=400)

    sucessos, erros = excluir_itens_lixeira(request.user, itens)
    if sucessos:
        messages.success(request, f'{sucessos} item(s) movido(s) para a lixeira.')
    if erros:
        messages.error(request, 'Alguns itens não puderam ser movidos para a lixeira.')
    return JsonResponse({'status': 'success'}, status=200)


@login_required
@user_passes_test(_is_superuser, login_url='inicio')
def ver_lixeira(request):
    filtro_nome = request.GET.get('nome', '').strip().lower()
    filtro_tipo = request.GET.get('tipo', '').strip()
    arquivos = listar_itens_lixeira(filtro_nome, filtro_tipo)
    return render(request, 'core/lixeira.html', {'arquivos': arquivos, 'filtro_nome': request.GET.get('nome', ''), 'filtro_tipo': filtro_tipo})


@login_required
@user_passes_test(_is_superuser, login_url='inicio')
@csrf_protect
def restaurar_arquivo(request):
    if request.method == 'POST':
        nome = os.path.basename(request.POST.get('caminho_lixeira', '').strip())
        registro = RegistroLixeira.objects.filter(nome_na_lixeira=nome).first()
        if registro:
            try:
                restaurar_item_lixeira(registro)
                messages.success(request, f'Restaurado com sucesso para: {registro.caminho_original}')
            except OSError:
                logger.exception('Falha ao restaurar item da lixeira')
                messages.error(request, 'Não foi possível restaurar o item.')
        else:
            messages.error(request, 'Não encontramos o registro de origem no banco de dados.')
    return redirect('ver_lixeira')


@login_required
@user_passes_test(_is_superuser, login_url='inicio')
@csrf_protect
def esvaziar_lixeira(request):
    if request.method == 'POST':
        pasta_lixeira = settings.LIXEIRA_DIR
        try:
            contador = executar_esvaziamento_lixeira(request.user)
            if contador is not None:
                messages.success(request, f'Sucesso! A lixeira foi esvaziada e {contador} itens foram apagados permanentemente do HD.') if contador else messages.info(request, 'A lixeira já estava vazia.')
            else:
                messages.error(request, 'Pasta da lixeira não encontrada no servidor.')
        except OSError:
            logger.exception('Falha ao esvaziar a lixeira')
            messages.error(request, 'Não foi possível esvaziar a lixeira.')
    return redirect('ver_lixeira')

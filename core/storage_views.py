import json
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .file_views import url_retorno_segura
from .storage_services import criar_subpasta_ged, salvar_upload_ged, upload_multiplo_permitido

logger = logging.getLogger(__name__)


@login_required
@require_POST
def upload_arquivo_geral(request):
    if request.FILES.get('arquivo'):
        arquivo = request.FILES['arquivo']
        caminho_pasta_atual = request.POST.get('caminho_destino') or request.POST.get('caminho_atual')
        url_retorno = request.POST.get('url_retorno', '/')

        try:
            nome_seguro, _ = salvar_upload_ged(request.user, arquivo, caminho_pasta_atual)
            messages.success(request, f"Arquivo '{nome_seguro}' enviado com sucesso!")
        except (PermissionDenied, ValidationError, OSError):
            logger.warning('Upload geral rejeitado', exc_info=True)
            messages.error(request, 'O upload não pôde ser concluído.')
        except Exception:
            logger.exception('Falha no upload geral do GED')
            messages.error(request, 'Não foi possível salvar o arquivo.')

        return redirect(url_retorno_segura(request, url_retorno, '/'))

    messages.error(request, 'Nenhum arquivo enviado.')
    return redirect('/')


@login_required
@csrf_protect
@require_POST
def upload_multiplo_ajax(request):
    if request.FILES.get('file'):
        arquivo = request.FILES['file']
        caminho_pasta_atual = request.POST.get('caminho_atual')
        if not upload_multiplo_permitido(caminho_pasta_atual):
            return JsonResponse({'error': 'Não é permitido fazer upload de arquivos diretamente na raiz deste módulo. Crie ou acesse uma pasta primeiro.'}, status=403)

        try:
            nome_seguro, _ = salvar_upload_ged(request.user, arquivo, caminho_pasta_atual)
        except PermissionDenied:
            logger.warning('Upload múltiplo negado', exc_info=True)
            return JsonResponse({'error': 'Você não tem permissão para este local.'}, status=403)
        except ValidationError:
            logger.warning('Upload múltiplo rejeitado por validação', exc_info=True)
            return JsonResponse({'error': 'O arquivo enviado não é válido.'}, status=400)
        except OSError:
            logger.exception('Falha de filesystem no upload múltiplo')
            return JsonResponse({'error': 'Não foi possível salvar o arquivo.'}, status=500)
        except Exception:
            logger.exception('Falha no upload múltiplo do GED')
            return JsonResponse({'error': 'Não foi possível salvar o arquivo.'}, status=500)

        return JsonResponse({'message': 'Sucesso!', 'nome': nome_seguro}, status=200)

    return JsonResponse({'error': 'Nenhum arquivo enviado.'}, status=400)


@login_required
@csrf_protect
@require_POST
def criar_subpasta(request):
    caminho_atual = request.POST.get('caminho_atual', '').strip()
    nome_pasta_input = request.POST.get('nome_pasta', '').strip()

    fallback = reverse('inicio')
    referer = request.META.get('HTTP_REFERER')
    try:
        criada, nome_pasta = criar_subpasta_ged(request.user, caminho_atual, nome_pasta_input)
        if criada:
            messages.success(request, f"Pasta '{nome_pasta}' criada com sucesso!")
        else:
            messages.error(request, f"A subpasta '{nome_pasta}' já existe neste local!")
    except ValidationError:
        logger.warning('Nome de subpasta rejeitado por validação', exc_info=True)
        messages.error(request, 'O nome da pasta não é válido.')
    except OSError:
        logger.exception('Falha ao criar subpasta do GED')
        messages.error(request, 'Não foi possível criar a pasta.')

    return redirect(url_retorno_segura(request, referer, fallback))

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from .forms import TramitacaoForm
from .models import Tramitacao
from .attachments import resolver_arquivos_upload
from .dispatch import criar_tramitacoes_para_usuario
from .permissions import setor_do_usuario
from .queries import listar_caixa_entrada
from .workflow import executar_acao_em_lote

logger = logging.getLogger(__name__)


@login_required
def caixa_entrada(request):
    recebidos = Tramitacao.objects.none()
    enviados = Tramitacao.objects.none()
    arquivados = Tramitacao.objects.none()
    concluidos = Tramitacao.objects.none()
    setor_usuario = setor_do_usuario(request.user)

    if setor_usuario:
        if request.method == 'POST':
            acao = request.POST.get('acao')
            ids_selecionados = request.POST.getlist('tramitacoes_ids')

            if ids_selecionados and acao:
                tramitacoes = Tramitacao.objects.filter(id__in=ids_selecionados, setor_destino=setor_usuario)
                try:
                    total = executar_acao_em_lote(tramitacoes, acao, request.user)
                    messages.success(request, f"{total} item(ns) processado(s).")
                except ValueError as exc:
                    messages.error(request, str(exc))
            return redirect('caixa_entrada')

        recebidos, enviados, arquivados, concluidos = listar_caixa_entrada(setor_usuario, request.user)

    form = TramitacaoForm()
    pag_recebidos = Paginator(recebidos, 10)
    recebidos_page = pag_recebidos.get_page(request.GET.get('page_rec'))
    pag_enviados = Paginator(enviados, 10)
    enviados_page = pag_enviados.get_page(request.GET.get('page_env'))
    pag_arquivados = Paginator(arquivados, 10)
    arquivados_page = pag_arquivados.get_page(request.GET.get('page_arq'))
    pag_concluidos = Paginator(concluidos, 10)
    concluidos_page = pag_concluidos.get_page(request.GET.get('page_conc'))

    context = {
        'recebidos': recebidos_page,
        'enviados': enviados_page,
        'arquivados': arquivados_page,
        'concluidos': concluidos_page,
        'setor_usuario': setor_usuario,
        'form': form,
    }
    return render(request, 'tramitacao/caixa_entrada.html', context)


@login_required
@transaction.atomic
def nova_tramitacao(request):
    if request.method == 'POST':
        form = TramitacaoForm(request.POST, request.FILES)

        if form.is_valid():
            arquivos = resolver_arquivos_upload(
                request.FILES,
                ['anexos', 'arquivo_anexo', 'arquivo'],
            )

            try:
                criadas = criar_tramitacoes_para_usuario(form.cleaned_data, request.user, arquivos)
            except ValueError as exc:
                logger.warning('Envio de tramitação rejeitado: %s', exc)
                messages.error(request, str(exc))
                return redirect('caixa_entrada')

            messages.success(request, f"{len(criadas)} tramitação(ões) enviada(s) com sucesso!")
            return redirect('caixa_entrada')
        logger.warning('Formulário de nova tramitação inválido: %s', form.errors)
        messages.error(request, "Não foi possível enviar a tramitação. Verifique os campos.")

    return redirect('caixa_entrada')

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .forms import RespostaTramitacaoForm, TramitacaoForm
from .models import Tramitacao
from .attachments import resolver_arquivos_upload
from .destinations import resolver_destinos_edicao
from .dispatch import (
    editar_tramitacao_devolvida as executar_edicao_devolvida,
    excluir_tramitacao_devolvida as executar_exclusao_devolvida,
)
from .permissions import obter_tramitacao_autorizada as obter_tramitacao_autorizada_service
from .responses import responder_tramitacao as executar_resposta
from .signatures import assinar_tramitacao_com_senha
from .workflow import (
    devolver_tramitacao as executar_devolucao,
    finalizar_tramitacao as executar_finalizacao,
    receber_tramitacao as executar_recebimento,
)

logger = logging.getLogger(__name__)


def obter_tramitacao_autorizada(request, pk, acao='visualizar'):
    try:
        return obter_tramitacao_autorizada_service(request.user, pk, acao)
    except Tramitacao.DoesNotExist:
        raise Http404('Tramitação não encontrada.')


@login_required
@transaction.atomic
def responder_tramitacao(request, pk):
    tramitacao = obter_tramitacao_autorizada(request, pk, 'responder')
    if request.method == 'POST':
        data = request.POST.copy()
        if not data.get('titulo'):
            data['titulo'] = tramitacao.titulo
        form = RespostaTramitacaoForm(data, request.FILES)
        if form.is_valid():
            arquivos = resolver_arquivos_upload(request.FILES, ['anexos', 'arquivo', 'arquivo_anexo'])
            try:
                executar_resposta(tramitacao, request.user, form.cleaned_data, arquivos)
            except ValueError as exc:
                logger.warning('Resposta de tramitação rejeitada: %s', exc)
                messages.error(request, str(exc), extra_tags='acao-bloqueada' if 'assinatura' in str(exc).lower() else '')
                return redirect('caixa_entrada')
            messages.success(request, 'Resposta enviada com sucesso!')
        else:
            logger.warning('Formulário de resposta inválido: %s', form.errors)
            messages.error(request, 'Não foi possível responder a tramitação. Verifique os campos.')
    return redirect('caixa_entrada')


@login_required
@require_POST
def receber_tramitacao(request, pk):
    tramitacao = obter_tramitacao_autorizada(request, pk, 'receber')
    try:
        executar_recebimento(tramitacao, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('caixa_entrada')
    messages.success(request, f'Tramitação {tramitacao.protocolo} recebida.')
    return redirect('caixa_entrada')


@login_required
def editar_tramitacao(request, pk):
    tramitacao = obter_tramitacao_autorizada(request, pk, 'editar')
    if request.method == 'POST':
        form = TramitacaoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                setor_destino, usuario_destino = resolver_destinos_edicao(form.cleaned_data, tramitacao.setor_destino)
                executar_edicao_devolvida(tramitacao, request.user, form.cleaned_data, setor_destino, usuario_destino)
            except ValueError as exc:
                logger.warning('Edição de tramitação rejeitada: %s', exc)
                messages.error(request, str(exc))
                return redirect('caixa_entrada')
            messages.success(request, 'Tramitação corrigida e reenviada com sucesso!')
        else:
            messages.error(request, 'Erro ao editar tramitação. Verifique os campos.')
    return redirect('caixa_entrada')


@login_required
@require_POST
def finalizar_tramitacao(request, pk):
    tramitacao = obter_tramitacao_autorizada(request, pk, 'finalizar')
    try:
        executar_finalizacao(tramitacao, request.user)
    except ValueError as exc:
        messages.error(request, str(exc), extra_tags='acao-bloqueada' if 'assinatura' in str(exc).lower() else '')
        return redirect('caixa_entrada')
    messages.success(request, f'Tramitação {tramitacao.protocolo} concluída.')
    return redirect('caixa_de_entrada')


@login_required
@require_POST
def devolver_tramitacao(request, pk):
    tramitacao = obter_tramitacao_autorizada(request, pk, 'devolver')
    try:
        executar_devolucao(tramitacao, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('caixa_entrada')
    messages.warning(request, f'Tramitação {tramitacao.protocolo} devolvida.')
    return redirect('caixa_entrada')


@login_required
@require_POST
def excluir_tramitacao_devolvida(request, pk):
    tramitacao = obter_tramitacao_autorizada(request, pk, 'excluir')
    try:
        executar_exclusao_devolvida(tramitacao, request.user)
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('caixa_de_entrada')


@login_required
def assinar_tramitacao(request, tramitacao_id):
    tramitacao = obter_tramitacao_autorizada(request, tramitacao_id, 'assinar')
    if request.method == 'POST':
        try:
            assinar_tramitacao_com_senha(tramitacao, request.user, request.POST.get('senha_confirmacao'))
        except ValueError as exc:
            mensagem = str(exc)
            if mensagem == 'Este documento não exige assinatura eletrônica.':
                messages.warning(request, mensagem)
            elif mensagem == 'Este documento já foi assinado anteriormente.':
                messages.info(request, mensagem)
            else:
                messages.error(request, mensagem)
            return redirect('caixa_de_entrada')
        messages.success(request, f"Documento assinado com sucesso por {request.user.get_full_name() or request.user.username}!")
    return redirect('caixa_de_entrada')

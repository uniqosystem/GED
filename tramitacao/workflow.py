"""Regras de transicao e operacoes de status da tramitacao."""

from django.utils import timezone

from core.models import LogAuditoria

from .models import Tramitacao

TRANSICOES_STATUS = {
    'RECEBER': {'PENDENTE': 'RECEBIDO'},
    'FINALIZAR': {'RECEBIDO': 'CONCLUIDO'},
    'DEVOLVER': {
        'PENDENTE': 'DEVOLVIDO',
        'RECEBIDO': 'DEVOLVIDO',
    },
    'RESPONDER': {
        'RECEBIDO': {'PENDENTE', 'CONCLUIDO'},
    },
}


def transicionar_status(tramitacao, evento, usuario, status_destino=None):
    estados_permitidos = TRANSICOES_STATUS.get(evento, {})
    estado_atual = tramitacao.status
    proximo_estado = estados_permitidos.get(estado_atual)

    if isinstance(proximo_estado, set):
        if status_destino not in proximo_estado:
            raise ValueError('A transição solicitada não é válida para esta tramitação.')
    elif status_destino and proximo_estado != status_destino:
        raise ValueError('A transição solicitada não é válida para esta tramitação.')
    elif not status_destino:
        status_destino = proximo_estado

    if not status_destino:
        raise ValueError('A tramitação não pode mudar de estado neste momento.')

    tramitacao.status = status_destino
    return tramitacao


def receber_tramitacao(tramitacao, usuario):
    transicionar_status(tramitacao, 'RECEBER', usuario)
    tramitacao.status = 'RECEBIDO'
    tramitacao.data_recebimento = timezone.now()
    if not tramitacao.usuario_destino and not tramitacao.assinaturas.exists():
        tramitacao.usuario_destino = usuario
    tramitacao.save()
    LogAuditoria.objects.create(
        usuario=usuario,
        acao='RECEBER_TRAMITACAO',
        descricao=f'Recebeu a tramitação de Protocolo: {tramitacao.protocolo}',
        caminho_item=f'Setor: {tramitacao.setor_destino}',
    )


def finalizar_tramitacao(tramitacao, usuario):
    if tramitacao.aguardar_resposta:
        raise ValueError('Esta tramitação aguarda uma resposta antes da conclusão.')
    if tramitacao.exige_assinatura and (
        not tramitacao.assinado or
        (tramitacao.assinaturas.exists() and tramitacao.assinaturas.filter(assinado=False).exists())
    ):
        raise ValueError('A assinatura é obrigatória antes da conclusão.')
    transicionar_status(tramitacao, 'FINALIZAR', usuario)
    tramitacao.status = 'CONCLUIDO'
    tramitacao.save()
    LogAuditoria.objects.create(
        usuario=usuario,
        acao='CONCLUIR_TRAMITACAO',
        descricao=f'Concluiu a tramitação de Protocolo: {tramitacao.protocolo}',
        caminho_item=f'Setor responsável: {tramitacao.setor_destino}',
    )


def devolver_tramitacao(tramitacao, usuario):
    transicionar_status(tramitacao, 'DEVOLVER', usuario)
    tramitacao.status = 'DEVOLVIDO'
    tramitacao.save()
    LogAuditoria.objects.create(
        usuario=usuario,
        acao='DEVOLVER_TRAMITACAO',
        descricao=f'Devolveu a tramitação de Protocolo: {tramitacao.protocolo}',
        caminho_item=f'Retornado para o setor: {tramitacao.setor_destino}',
    )


def marcar_recebido(tramitacoes, usuario):
    total = 0
    for tramitacao in tramitacoes.filter(status='PENDENTE'):
        receber_tramitacao(tramitacao, usuario)
        total += 1
    return total


def arquivar_tramitacoes(tramitacoes):
    return tramitacoes.filter(status__in={'PENDENTE', 'RECEBIDO'}).update(status='ARQUIVADO')


def desarquivar_tramitacoes(tramitacoes):
    return tramitacoes.filter(status='ARQUIVADO').update(status='RECEBIDO')


def executar_acao_em_lote(tramitacoes, acao, usuario):
    if acao == 'marcar_lido':
        return marcar_recebido(tramitacoes, usuario)
    if acao == 'concluir':
        total = 0
        for tramitacao in tramitacoes:
            finalizar_tramitacao(tramitacao, usuario)
            total += 1
        return total
    if acao == 'arquivar':
        return arquivar_tramitacoes(tramitacoes)
    if acao == 'desarquivar':
        return desarquivar_tramitacoes(tramitacoes)
    raise ValueError('Ação em lote inválida.')

"""Regras de resposta e despacho da tramitacao."""

from django.contrib.auth.models import User

from core.models import LogAuditoria

from .attachments import adicionar_anexos_tramitacao
from .models import HistoricoTramitacao
from .workflow import transicionar_status


def responder_tramitacao(tramitacao, usuario, dados, arquivos):
    if not tramitacao.aguardar_resposta:
        raise ValueError('Esta tramitação não exige resposta.')

    remetente_original = tramitacao.remetente_original or tramitacao.remetente
    setor_origem_original = tramitacao.setor_origem_original or tramitacao.setor_origem
    status_resposta = 'PENDENTE' if dados.get('aguardar_resposta', False) else 'CONCLUIDO'
    if tramitacao.exige_assinatura and not tramitacao.assinado:
        raise ValueError('A assinatura é obrigatória antes da resposta.')
    transicionar_status(tramitacao, 'RESPONDER', usuario, status_resposta)

    setor_destino = tramitacao.setor_origem
    perfil_usuario = getattr(usuario, 'perfil', None)
    setor_origem = perfil_usuario.setor if perfil_usuario else None
    if not setor_origem:
        raise ValueError('O usuário não possui setor vinculado.')

    tramitacao.setor_origem = setor_origem
    tramitacao.setor_destino = setor_destino
    tramitacao.remetente = usuario
    tramitacao.remetente_original = remetente_original
    tramitacao.setor_origem_original = setor_origem_original
    tramitacao.titulo = dados.get('titulo') or tramitacao.titulo
    tramitacao.despacho = dados['despacho']
    tramitacao.observacao = dados.get('observacao', '')
    tramitacao.aguardar_resposta = bool(dados.get('aguardar_resposta', False))
    usuario_destino_id = dados.get('usuario_destino')
    usuario_destino = User.objects.filter(pk=usuario_destino_id).first() if usuario_destino_id else None
    if usuario_destino:
        perfil_destino = getattr(usuario_destino, 'perfil', None)
        if not perfil_destino or perfil_destino.setor_id != setor_destino.id:
            raise ValueError('O usuário selecionado não pertence ao setor de destino.')
    tramitacao.usuario_destino = usuario_destino
    tramitacao.auto_devolvido = False
    tramitacao.save()

    historico = HistoricoTramitacao.objects.create(
        tramitacao=tramitacao,
        remetente=usuario,
        setor_origem=setor_origem,
        despacho=tramitacao.despacho,
        aguardar_resposta=tramitacao.aguardar_resposta,
    )
    adicionar_anexos_tramitacao(tramitacao, historico, arquivos)

    LogAuditoria.objects.create(
        usuario=usuario,
        acao='RESPONDER_TRAMITACAO',
        descricao=f'Respondeu à tramitação de Protocolo: {tramitacao.protocolo}',
        caminho_item=f'Destino: {tramitacao.setor_destino}',
    )

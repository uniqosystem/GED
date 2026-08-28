"""Criacao e reenvio de tramitacoes."""

from django.contrib.auth.models import User

from core.models import LogAuditoria, Setor

from .attachments import adicionar_anexos_tramitacao
from .models import HistoricoTramitacao, Tramitacao


def criar_tramitacoes(dados, usuario, setor_origem, setores_destino, usuarios_destino, arquivos):
    if not setor_origem:
        raise ValueError('O usuário remetente não possui setor vinculado.')

    setores_destino = list(setores_destino)
    usuarios_destino = list(usuarios_destino) if usuarios_destino else []
    setores_destino_ids = {setor.id for setor in setores_destino}

    for usuario_destino in usuarios_destino:
        perfil_destino = getattr(usuario_destino, 'perfil', None)
        if not perfil_destino or perfil_destino.setor_id not in setores_destino_ids:
            raise ValueError('O usuário selecionado não pertence a um setor de destino.')

    criadas = []
    destinatarios = usuarios_destino if usuarios_destino else [None]

    for setor_destino in setores_destino:
        for usuario_destino in destinatarios:
            tramitacao = Tramitacao(
                tipo_documento=dados['tipo_documento'],
                titulo=dados['titulo'],
                despacho=dados['despacho'],
                observacao=dados.get('observacao', ''),
                aguardar_resposta=dados.get('aguardar_resposta', False),
                exige_assinatura=dados.get('exige_assinatura', False),
                data_limite_resposta=dados.get('data_limite_resposta'),
                setor_destino=setor_destino,
                usuario_destino=usuario_destino,
                remetente=usuario,
                remetente_original=usuario,
                criador=usuario,
                setor_origem=setor_origem,
                setor_origem_original=setor_origem,
                setor_criador=setor_origem,
                status='PENDENTE',
            )
            tramitacao.save()
            historico = HistoricoTramitacao.objects.create(
                tramitacao=tramitacao,
                remetente=usuario,
                setor_origem=setor_origem,
                despacho=tramitacao.despacho,
                aguardar_resposta=tramitacao.aguardar_resposta,
            )
            adicionar_anexos_tramitacao(tramitacao, historico, arquivos)
            criadas.append(tramitacao)

    return criadas


def criar_tramitacoes_para_usuario(dados, usuario, arquivos):
    perfil = getattr(usuario, 'perfil', None)
    setor_origem = perfil.setor if perfil else None
    if not setor_origem:
        raise ValueError('O usuário remetente não possui setor vinculado.')

    setores_ids = dados.get('setor_destino', [])
    setores_destino = Setor.objects.all() if 'todos' in setores_ids or not setores_ids else Setor.objects.filter(id__in=setores_ids)
    usuarios_ids = dados.get('usuario_destino', [])
    usuarios_destino = User.objects.filter(id__in=usuarios_ids) if usuarios_ids else None

    return criar_tramitacoes(dados, usuario, setor_origem, setores_destino, usuarios_destino, arquivos)


def editar_tramitacao(tramitacao, dados, setor_destino, usuario_destino):
    tramitacao.tipo_documento = dados['tipo_documento']
    tramitacao.titulo = dados['titulo']
    tramitacao.despacho = dados['despacho']
    tramitacao.observacao = dados.get('observacao', '')
    tramitacao.aguardar_resposta = dados.get('aguardar_resposta', False)
    tramitacao.exige_assinatura = dados.get('exige_assinatura', tramitacao.exige_assinatura)
    tramitacao.data_limite_resposta = dados.get('data_limite_resposta')
    tramitacao.setor_destino = setor_destino
    tramitacao.usuario_destino = usuario_destino
    tramitacao.status = 'PENDENTE'
    tramitacao.assinado = False
    tramitacao.assinado_por = None
    tramitacao.data_assinatura = None
    tramitacao.save()
    return tramitacao


def editar_tramitacao_devolvida(tramitacao, usuario, dados, setor_destino, usuario_destino):
    if tramitacao.status != 'DEVOLVIDO':
        raise ValueError('Esta tramitação não pode ser editada.')

    editar_tramitacao(tramitacao, dados, setor_destino, usuario_destino)
    LogAuditoria.objects.create(
        usuario=usuario,
        acao='EDITAR_TRAMITACAO',
        descricao=f'Editou os dados do Protocolo: {tramitacao.protocolo}',
        caminho_item=f'Alterações realizadas por {usuario.username}',
    )
    return tramitacao


def excluir_tramitacao_devolvida(tramitacao, usuario):
    if tramitacao.status != 'DEVOLVIDO':
        raise ValueError('Esta tramitação não pode ser excluída.')
    protocolo = tramitacao.protocolo
    tramitacao.delete()
    LogAuditoria.objects.create(
        usuario=usuario,
        acao='EXCLUIR_TRAMITACAO',
        descricao=f'Excluiu permanentemente à tramitação de Protocolo: {protocolo}',
        caminho_item='Origem/Destino envolvidos',
    )

"""Autorizacao e acesso a tramitacoes."""

from django.core.exceptions import PermissionDenied

from .models import Tramitacao


def setor_do_usuario(usuario):
    perfil = getattr(usuario, 'perfil', None)
    return perfil.setor if perfil and perfil.setor else None


def usuario_tem_acesso_tramitacao(usuario, tramitacao, acao='visualizar'):
    if usuario.is_superuser:
        return True

    setor_usuario = setor_do_usuario(usuario)
    if not setor_usuario:
        return False

    setor_destino = tramitacao.setor_destino_id == setor_usuario.id
    usuario_destino = (
        setor_destino and
        (tramitacao.usuario_destino_id is None or tramitacao.usuario_destino_id == usuario.id)
    )
    setor_origem = (
        tramitacao.setor_origem_id == setor_usuario.id or
        tramitacao.setor_origem_original_id == setor_usuario.id
    )

    if acao in {'receber', 'responder', 'finalizar', 'devolver', 'assinar'}:
        return usuario_destino
    if acao in {'editar', 'excluir'}:
        return setor_origem
    return usuario_destino or setor_origem


def obter_tramitacao_autorizada(usuario, pk, acao='visualizar'):
    tramitacao = Tramitacao.objects.select_related(
        'criador', 'remetente', 'setor_origem', 'setor_destino', 'usuario_destino'
    ).filter(pk=pk).first()
    if not tramitacao:
        raise Tramitacao.DoesNotExist()
    if not usuario_tem_acesso_tramitacao(usuario, tramitacao, acao):
        raise PermissionDenied('Você não tem permissão para acessar esta tramitação.')
    return tramitacao

"""Resolucao e validacao de destinos da tramitacao."""

from django.contrib.auth.models import User

from core.models import Setor


def usuario_destino_unico(form):
    usuarios_ids = form.cleaned_data.get('usuario_destino', [])
    if len(usuarios_ids) > 1:
        form.add_error('usuario_destino', 'Selecione apenas um usuário de destino.')
        return None
    if not usuarios_ids:
        return None
    return User.objects.filter(pk=usuarios_ids[0]).first()


def setor_destino_unico(form, atual):
    setores_ids = form.cleaned_data.get('setor_destino', [])
    if 'todos' in setores_ids or not setores_ids:
        return atual
    if len(setores_ids) > 1:
        form.add_error('setor_destino', 'Selecione apenas um setor de destino.')
        return None
    return Setor.objects.filter(pk=setores_ids[0]).first()


def resolver_destinos_edicao(dados, setor_atual):
    setores_ids = dados.get('setor_destino', [])
    if 'todos' in setores_ids or not setores_ids:
        setor_destino = setor_atual
    elif len(setores_ids) > 1:
        raise ValueError('Selecione apenas um setor de destino.')
    else:
        setor_destino = Setor.objects.filter(pk=setores_ids[0]).first()
    if not setor_destino:
        raise ValueError('Selecione um setor de destino válido.')

    usuarios_ids = dados.get('usuario_destino', [])
    if len(usuarios_ids) > 1:
        raise ValueError('Selecione apenas um usuário de destino.')
    usuario_destino = User.objects.filter(pk=usuarios_ids[0]).first() if usuarios_ids else None
    if usuarios_ids and not usuario_destino:
        raise ValueError('Selecione um usuário de destino válido.')
    if usuario_destino:
        perfil_destino = getattr(usuario_destino, 'perfil', None)
        if not perfil_destino or perfil_destino.setor_id != setor_destino.id:
            raise ValueError('O usuário selecionado não pertence ao setor de destino.')
    return setor_destino, usuario_destino

"""Consultas de leitura reutilizaveis do dominio de tramitacao."""

from django.contrib.auth.models import User
from django.db.models import Q

from core.models import Perfil

from .models import Tramitacao


def listar_usuarios_por_setores(setores_ids):
    if not setores_ids:
        return []

    perfis = Perfil.objects.filter(setor_id__in=setores_ids).select_related('user', 'setor')
    usuarios_list = []
    usuarios_vistos = set()

    for perfil in perfis:
        if perfil.user and perfil.user.id not in usuarios_vistos:
            usuarios_vistos.add(perfil.user.id)
            nome_usuario = perfil.user.get_full_name() or perfil.user.username
            setor_nome = perfil.setor.nome if perfil.setor else 'Sem Setor'
            usuarios_list.append({
                'id': perfil.user.id,
                'nome': nome_usuario,
                'setor': setor_nome,
            })

    return usuarios_list


def listar_caixa_entrada(setor_usuario, usuario):
    if not setor_usuario:
        vazio = Tramitacao.objects.none()
        return vazio, vazio, vazio, vazio

    base_query = Tramitacao.objects.select_related(
        'criador', 'setor_criador', 'remetente', 'setor_origem', 'setor_destino', 'usuario_destino'
    ).prefetch_related('anexos')

    recebidos = base_query.filter(
        setor_destino=setor_usuario,
        status__in=['PENDENTE', 'RECEBIDO'],
    ).filter(
        Q(usuario_destino__isnull=True) | Q(usuario_destino=usuario)
    ).order_by('-data_envio')

    enviados = base_query.filter(
        Q(setor_origem=setor_usuario) | Q(setor_origem_original=setor_usuario)
    ).exclude(status='CONCLUIDO').distinct().order_by('-data_envio')
    arquivados = base_query.filter(setor_destino=setor_usuario, status='ARQUIVADO').order_by('-data_envio')
    concluidos = base_query.filter(
        Q(setor_destino=setor_usuario)
        | Q(setor_origem_original=setor_usuario)
        | Q(setor_origem=setor_usuario),
        status='CONCLUIDO',
    ).distinct().order_by('-data_envio')
    return recebidos, enviados, arquivados, concluidos


def listar_anexos_tramitacao(tramitacao):
    return [
        {
            'nome': anexo.arquivo.name.split('/')[-1].split('\\')[-1],
            'url': anexo.arquivo.url,
        }
        for anexo in tramitacao.anexos.all()
    ]


def contar_notificacoes_pendentes(usuario):
    if not getattr(usuario, 'is_authenticated', False):
        return 0

    setor_usuario = getattr(getattr(usuario, 'perfil', None), 'setor', None)
    if not setor_usuario:
        return 0

    return Tramitacao.objects.filter(
        setor_destino=setor_usuario,
        status='PENDENTE',
    ).count()

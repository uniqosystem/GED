"""Regras de assinatura eletronica da tramitacao."""

from django.contrib.auth import authenticate
from django.utils import timezone

from core.models import LogAuditoria
from .models import AssinaturaTramitacao


def assinar_tramitacao(tramitacao, usuario):
    if tramitacao.status != 'RECEBIDO':
        raise ValueError('A tramitação precisa ser recebida antes da assinatura.')
    if not tramitacao.exige_assinatura:
        raise ValueError('Este documento não exige assinatura eletrônica.')
    if tramitacao.assinado and tramitacao.assinado_por_id == usuario.id and not tramitacao.assinaturas.exists():
        raise ValueError('Este documento já foi assinado anteriormente.')
    assinatura, criada = AssinaturaTramitacao.objects.get_or_create(
        tramitacao=tramitacao,
        usuario=usuario,
    )
    if not criada and assinatura.assinado:
        raise ValueError('Este documento já foi assinado anteriormente.')
    assinatura.assinado = True
    assinatura.data_assinatura = timezone.now()
    assinatura.save(update_fields=['assinado', 'data_assinatura'])
    if not tramitacao.assinado:
        tramitacao.assinado_por = usuario
        tramitacao.data_assinatura = assinatura.data_assinatura
    tramitacao.assinado = not tramitacao.assinaturas.filter(assinado=False).exists()
    tramitacao.save()
    LogAuditoria.objects.create(
        usuario=usuario,
        acao='ASSINAR_TRAMITACAO',
        descricao=(
            f'Assinou eletronicamente a tramitação protocolo {tramitacao.protocolo} '
            f'(Nome: {usuario.get_full_name() or usuario.username}).'
        ),
        caminho_item=str(tramitacao.id),
    )


def assinar_tramitacao_com_senha(tramitacao, usuario, senha):
    if not senha:
        raise ValueError('Você deve informar sua senha para confirmar a assinatura.')
    if authenticate(username=usuario.username, password=senha) is None:
        raise ValueError('Senha incorreta. A assinatura eletrônica foi cancelada.')
    assinar_tramitacao(tramitacao, usuario)
    return tramitacao

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse

from .models import Tramitacao
from .history import montar_historico_tramitacao
from .permissions import obter_tramitacao_autorizada
from .queries import (
    contar_notificacoes_pendentes,
    listar_anexos_tramitacao,
    listar_usuarios_por_setores,
)


@login_required
def api_historico_tramitacao(request, pk):
    try:
        tramitacao = obter_tramitacao_autorizada(request.user, pk)
    except Tramitacao.DoesNotExist:
        raise Http404('Tramitação não encontrada.')
    assinaturas = [
        {
            'usuario': assinatura.usuario.get_full_name() or assinatura.usuario.username,
            'data': assinatura.data_assinatura.strftime('%d/%m/%Y %H:%M'),
        }
        for assinatura in tramitacao.assinaturas.select_related('usuario').filter(assinado=True)
    ]
    return JsonResponse({'historico': montar_historico_tramitacao(tramitacao), 'assinaturas': assinaturas})


@login_required
def ajax_usuarios_setores(request):
    setores_ids = request.GET.getlist('setor_id')
    return JsonResponse({'usuarios': listar_usuarios_por_setores(setores_ids)})


@login_required
def listar_anexos_json(request, pk):
    try:
        tramitacao = obter_tramitacao_autorizada(request.user, pk)
    except Tramitacao.DoesNotExist:
        raise Http404('Tramitação não encontrada.')
    return JsonResponse({'anexos': listar_anexos_tramitacao(tramitacao)})


def verificar_notificacoes(request):
    return JsonResponse({'total': contar_notificacoes_pendentes(request.user)})

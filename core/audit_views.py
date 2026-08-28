from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from .audit_queries import filtrar_logs_auditoria
from .models import LogAuditoria


def _is_superuser(user):
    return user.is_superuser


@login_required
@user_passes_test(_is_superuser, login_url='inicio')
def ver_auditoria(request):
    filtro_busca = request.GET.get('busca', '').strip()
    filtro_acao = request.GET.get('acao', '').strip()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()
    logs_list = filtrar_logs_auditoria(filtro_busca, filtro_acao, data_inicio, data_fim)

    pagina_logs = Paginator(logs_list, 20).get_page(request.GET.get('page', 1))
    return render(request, 'core/auditoria.html', {
        'logs': pagina_logs,
        'filtro_busca': filtro_busca,
        'filtro_acao': filtro_acao,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'acoes_choices': LogAuditoria.ACOES_CHOICES,
    })


@login_required
@user_passes_test(_is_superuser, login_url='inicio')
def exportar_auditoria(request):
    return HttpResponse('Em desenvolvimento...')

from django.db.models import Q

from .models import LogAuditoria


def filtrar_logs_auditoria(busca='', acao='', data_inicio='', data_fim=''):
    logs = LogAuditoria.objects.select_related('usuario').all()
    if busca:
        logs = logs.filter(
            Q(descricao__icontains=busca)
            | Q(usuario__username__icontains=busca)
            | Q(usuario__first_name__icontains=busca)
            | Q(usuario__last_name__icontains=busca)
        )
    if acao:
        logs = logs.filter(acao=acao)
    if data_inicio:
        logs = logs.filter(data_hora__date__gte=data_inicio)
    if data_fim:
        logs = logs.filter(data_hora__date__lte=data_fim)
    return logs
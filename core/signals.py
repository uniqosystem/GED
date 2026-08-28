from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import LogAuditoria

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    LogAuditoria.objects.create(
        usuario=user,
        acao='LOGIN',
        descricao=f"Usuário {user.username} realizou login no sistema."
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    if user: # Verifica se o usuário ainda está disponível no contexto
        LogAuditoria.objects.create(
            usuario=user,
            acao='LOGOUT',
            descricao=f"Usuário {user.username} encerrou a sessão."
        )
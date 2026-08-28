"""Views de autenticacao, sessao e verificacao de disponibilidade."""

import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
def health_check(request):
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({'status': 'unhealthy'}, status=503)
    return JsonResponse({'status': 'ok'})


def inicio(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user is not None:
            login(request, user)
            perfil = getattr(user, 'perfil', None)
            if perfil and not perfil.password_changed:
                return redirect('change_password')
            return redirect('inicio_sistema')
        return render(request, 'core/login.html', {'error': 'Usuário ou senha inválidos'})
    return render(request, 'core/login.html')


@login_required
def change_password(request):
    """View para alteração obrigatória de senha no primeiro acesso."""
    perfil = getattr(request.user, 'perfil', None)
    if perfil and perfil.password_changed:
        return redirect('inicio_sistema')

    if request.method == 'POST':
        senha_atual = request.POST.get('senha_atual', '')
        senha_nova = request.POST.get('senha_nova', '')
        senha_confirmacao = request.POST.get('senha_confirmacao', '')
        erros = []

        if not senha_atual:
            erros.append('Informe sua senha atual.')
        elif not authenticate(username=request.user.username, password=senha_atual):
            erros.append('Senha atual incorreta.')

        if not senha_nova:
            erros.append('Informe uma nova senha.')
        elif len(senha_nova) < 8:
            erros.append('A nova senha deve ter no mínimo 8 caracteres.')
        elif senha_nova == senha_atual:
            erros.append('A nova senha não pode ser igual à senha anterior.')

        if senha_nova:
            try:
                validate_password(senha_nova, user=request.user)
            except ValidationError as exc:
                erros.extend(exc.messages)

        if senha_nova != senha_confirmacao:
            erros.append('As senhas não conferem.')

        if erros:
            return render(request, 'core/change_password.html', {'erros': erros})

        try:
            request.user.set_password(senha_nova)
            request.user.save()
            if perfil:
                perfil.password_changed = True
                perfil.password_change_date = timezone.now()
                perfil.save()
            user = authenticate(username=request.user.username, password=senha_nova)
            if user:
                login(request, user)
            messages.success(request, 'Senha alterada com sucesso! Bem-vindo ao sistema.')
            return redirect('inicio_sistema')
        except Exception:
            logger.exception('Erro ao alterar senha do usuário')
            return render(request, 'core/change_password.html', {'erros': ['Não foi possível alterar sua senha. Tente novamente.']})

    return render(request, 'core/change_password.html')


@login_required
def pagina_inicial_direcionamento(request):
    return render(request, 'core/inicio.html')


@login_required
def logout_usuario(request):
    logout(request)
    return redirect('inicio')

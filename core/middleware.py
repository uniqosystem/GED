"""
Middleware para enforçar alteração obrigatória de senha no primeiro acesso.
"""
import logging
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger(__name__)

# Rotas que podem ser acessadas sem alterar a senha
ROTAS_PERMITIDAS = [
    'change_password',  # Nome da URL para alterar senha
    'logout',  # Permitir logout
    'health_check',  # Health check
]

class EnforcePasswordChangeMiddleware:
    """
    Middleware que força a alteração de senha no primeiro acesso.
    
    Se o usuário está autenticado mas não mudou a senha, redireciona
    para a página de alteração de senha. Permite apenas rotas específicas.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Só aplica para usuários autenticados
        if request.user.is_authenticated:
            # Verifica se o usuário precisa alterar a senha
            perfil = getattr(request.user, 'perfil', None)
            
            if perfil and not perfil.password_changed:
                # Obtém o nome da view/URL atual
                nome_view_atual = request.resolver_match.url_name if request.resolver_match else None
                caminhos_permitidos = {reverse(rota) for rota in ROTAS_PERMITIDAS}
                
                # Se não está na página de alteração de senha, redireciona
                if (
                    nome_view_atual not in ROTAS_PERMITIDAS and
                    request.path not in caminhos_permitidos
                ):
                    return redirect('change_password')
        
        response = self.get_response(request)
        return response

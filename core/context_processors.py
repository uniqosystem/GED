from django.conf import settings

from ponto.permissions import is_ponto_rh

from eventos.permissions import pode_gerenciar_eventos


def usuario_setor(request):
    if request.user.is_authenticated:
        # Tenta buscar o setor do usuário pelo perfil ou atributo direto
        setor = None
        perfil = getattr(request.user, 'perfil', None)
        if perfil and hasattr(perfil, 'setor'):
            setor = perfil.setor
        elif hasattr(request.user, 'setor'):
            setor = request.user.setor

        grupos_pf_pj = set(getattr(settings, 'GED_PF_GROUPS', [])) | set(getattr(settings, 'GED_PJ_GROUPS', []))
        grupos_setores_menu = [
            grupo for grupo in request.user.groups.all()
            if grupo.name not in grupos_pf_pj
        ]

        return {
            'setor_usuario': setor,
            'grupos_setores_menu': grupos_setores_menu,
            'pode_gerenciar_ponto': is_ponto_rh(request.user),
            'pode_gerenciar_eventos': pode_gerenciar_eventos(request.user),
        }
    return {
        'setor_usuario': None,
        'grupos_setores_menu': [],
        'pode_gerenciar_ponto': False,
        'pode_gerenciar_eventos': False,
    }

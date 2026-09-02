import unicodedata

from django.conf import settings


def _normalizar_grupo(nome):
    sem_acentos = unicodedata.normalize('NFKD', nome)
    sem_acentos = ''.join(caractere for caractere in sem_acentos if not unicodedata.combining(caractere))
    return ' '.join(sem_acentos.upper().split())


def is_ponto_rh(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True

    grupos_permitidos = {
        _normalizar_grupo(nome)
        for nome in getattr(settings, 'PONTO_RH_GROUPS', [])
    }
    grupos_usuario = {
        _normalizar_grupo(grupo.name)
        for grupo in user.groups.all()
    }
    return bool(grupos_usuario.intersection(grupos_permitidos))
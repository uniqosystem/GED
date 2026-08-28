import mimetypes
import os

from django.core.exceptions import PermissionDenied
from django.utils.http import url_has_allowed_host_and_scheme

from .file_services import validar_acesso_ged, validar_caminho_seguro


def url_retorno_segura(request, valor, fallback):
    if valor and url_has_allowed_host_and_scheme(
        valor,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return valor
    return fallback


def abrir_arquivo_autorizado(usuario, caminho_solicitado):
    caminho_seguro = validar_caminho_seguro(caminho_solicitado)
    validar_acesso_ged(usuario, caminho_seguro)
    if not os.path.isfile(caminho_seguro):
        raise FileNotFoundError(caminho_seguro)
    return open(caminho_seguro, 'rb'), caminho_seguro


def tipo_conteudo_arquivo(caminho):
    return mimetypes.guess_type(caminho)[0] or 'application/octet-stream'
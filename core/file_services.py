"""Servicos de acesso seguro ao filesystem do GED."""

import os
import re
import unicodedata

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError

from .file_validation import validar_upload


def validar_caminho_seguro(caminho_solicitado, verificar_existencia=True):
    raizes_autorizadas = [
        os.path.realpath(settings.GED_BASE_DIR),
        os.path.realpath(settings.SETORES_BASE_DIR),
        os.path.realpath(settings.TRAMITACAO_DIR),
        os.path.realpath(settings.LIXEIRA_DIR),
    ]
    if not caminho_solicitado:
        return raizes_autorizadas[0]

    caminho_alvo = os.path.realpath(caminho_solicitado)
    try:
        esta_em_raiz_autorizada = any(
            os.path.commonpath([caminho_alvo, base]) == os.path.normpath(base)
            for base in raizes_autorizadas
        )
    except ValueError:
        esta_em_raiz_autorizada = False

    if not esta_em_raiz_autorizada:
        raise PermissionDenied(f"Acesso negado: {caminho_alvo} fora da área permitida.")
    if verificar_existencia and not os.path.exists(caminho_alvo):
        raise PermissionDenied("Acesso negado: Caminho não encontrado.")
    return caminho_alvo


def _normalizar_nome_setor(nome):
    valor = unicodedata.normalize('NFKD', str(nome).strip())
    valor = ''.join(char for char in valor if not unicodedata.combining(char))
    valor = valor.casefold()
    valor = re.sub(r'[^a-z0-9]+', '', valor)
    return valor


def _caminho_esta_em(caminho, raiz):
    try:
        return os.path.commonpath([
            os.path.normcase(os.path.abspath(caminho)),
            os.path.normcase(os.path.abspath(raiz)),
        ]) == os.path.normcase(os.path.abspath(raiz))
    except ValueError:
        return False


def usuario_pode_acessar_caminho(usuario, caminho, permitir_raiz_setores=False):
    if not usuario or not usuario.is_authenticated:
        return False

    grupos_usuario = {_normalizar_nome_setor(grupo.name) for grupo in usuario.groups.all()}
    if usuario.is_superuser or 'ged_administrador' in grupos_usuario:
        return True

    caminho_alvo = os.path.abspath(caminho)
    raiz_ged = os.path.abspath(settings.GED_BASE_DIR)
    raiz_setores = os.path.abspath(settings.SETORES_BASE_DIR)
    if _caminho_esta_em(caminho_alvo, raiz_setores):
        relativo = os.path.relpath(caminho_alvo, raiz_setores)
        if relativo == '.':
            return permitir_raiz_setores
        nome_setor = _normalizar_nome_setor(relativo.split(os.sep)[0])
        perfil = getattr(usuario, 'perfil', None)
        if perfil and perfil.setor:
            grupos_usuario.add(_normalizar_nome_setor(perfil.setor.nome))
        return nome_setor in grupos_usuario

    raiz_pf = os.path.join(raiz_ged, 'PESSOA FISICA')
    raiz_pj = os.path.join(raiz_ged, 'PESSOA JURIDICA')
    if _caminho_esta_em(caminho_alvo, raiz_pf):
        return bool(grupos_usuario.intersection({_normalizar_nome_setor(group) for group in settings.GED_PF_GROUPS}))
    if _caminho_esta_em(caminho_alvo, raiz_pj):
        return bool(grupos_usuario.intersection({_normalizar_nome_setor(group) for group in settings.GED_PJ_GROUPS}))
    return False


def validar_acesso_ged(usuario, caminho, permitir_raiz_setores=False):
    if not usuario_pode_acessar_caminho(usuario, caminho, permitir_raiz_setores):
        raise PermissionDenied('Você não tem permissão para acessar este local.')
    return caminho


def secure_filename(filename):
    return re.sub(r'[^a-zA-Z0-9._-]', '_', filename)


def validar_nome_seguro(nome_item, eh_arquivo=False):
    if not nome_item or nome_item in {'.', '..'}:
        raise ValidationError('O nome do item é inválido.')
    if any(caractere in nome_item for caractere in '<>:"/\\|?*'):
        raise ValidationError('O nome do item contém caracteres inválidos.')
    if nome_item[-1] in {' ', '.'}:
        raise ValidationError('O nome do item não pode terminar com espaço ou ponto.')

    nomes_reservados = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
    }
    nome_puro = os.path.splitext(nome_item)[0].upper().strip()
    if nome_puro in nomes_reservados:
        raise ValidationError(f"O nome '{nome_item}' é reservado pelo sistema operacional Windows e não pode ser usado.")
    if eh_arquivo:
        extensao = os.path.splitext(nome_item)[1].lower()
        if extensao in {'.exe', '.bat', '.cmd', '.msi', '.vbs', '.vbe', '.js', '.jse', '.wsf', '.wsh', '.ps1', '.scr', '.com', '.pif', '.hta', '.sh'}:
            raise ValidationError(f"Arquivos com a extensão '{extensao}' são bloqueados por motivos de segurança.")


def salvar_upload_ged(usuario, arquivo, caminho_destino):
    from .storage_services import salvar_upload_ged as salvar_upload
    return salvar_upload(usuario, arquivo, caminho_destino)



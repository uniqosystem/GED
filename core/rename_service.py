"""Operacoes de renomeacao segura no filesystem do GED."""

import os

from django.core.exceptions import ValidationError

from .file_services import validar_acesso_ged, validar_caminho_seguro, validar_nome_seguro


def renomear_item(usuario, caminho_atual, novo_nome):
    nome_base_original, extensao_original = os.path.splitext(os.path.basename(caminho_atual))
    nome_limpo = os.path.splitext(os.path.basename(novo_nome.strip()))[0]
    nome_final = f'{nome_limpo}{extensao_original}'

    caminho_origem = validar_caminho_seguro(caminho_atual, verificar_existencia=True)
    validar_acesso_ged(usuario, caminho_origem)

    nome_base, extensao = os.path.splitext(nome_final)
    if not extensao and os.path.isfile(caminho_origem):
        _, extensao_original = os.path.splitext(caminho_origem)
        nome_final = f'{nome_base}{extensao_original}'

    validar_nome_seguro(nome_final, eh_arquivo=os.path.isfile(caminho_origem))
    caminho_novo = os.path.join(os.path.dirname(caminho_origem), nome_final)
    validar_caminho_seguro(caminho_novo, verificar_existencia=False)

    if os.path.exists(caminho_novo):
        return False, True
    if not os.path.exists(caminho_origem):
        return False, False

    try:
        os.rename(caminho_origem, caminho_novo)
    except OSError as exc:
        raise OSError('Não foi possível renomear o item.') from exc
    return True, False

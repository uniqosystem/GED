import logging
import os
import shutil
import time
from datetime import datetime

from django.conf import settings

from .file_services import validar_acesso_ged, validar_caminho_seguro
from .models import LogAuditoria, RegistroLixeira

logger = logging.getLogger(__name__)


def mover_para_lixeira(usuario, caminho_atual):
    caminho_seguro = validar_caminho_seguro(caminho_atual)
    validar_acesso_ged(usuario, caminho_seguro)
    nome_item = os.path.basename(caminho_seguro)
    os.makedirs(settings.LIXEIRA_DIR, exist_ok=True)
    caminho_lixeira = os.path.join(
        settings.LIXEIRA_DIR,
        f"{datetime.now():%Y%m%d%H%M%S}_{nome_item}",
    )

    for tentativa in range(3):
        try:
            shutil.move(caminho_seguro, caminho_lixeira)
            break
        except (PermissionError, OSError):
            logger.warning('Tentativa de mover item falhou: %s', caminho_seguro, exc_info=True)
            if tentativa == 2:
                return False, nome_item
            time.sleep(0.5)

    try:
        RegistroLixeira.objects.create(
            nome_na_lixeira=os.path.basename(caminho_lixeira),
            caminho_original=caminho_seguro,
            apagado_por=usuario,
        )
    except Exception:
        logger.exception('Falha ao registrar item movido para a lixeira')
        shutil.move(caminho_lixeira, caminho_seguro)
        raise

    LogAuditoria.objects.create(
        usuario=usuario,
        acao='APAGAR',
        descricao=nome_item,
        caminho_item=caminho_seguro,
    )
    return True, nome_item


def restaurar_item_lixeira(registro):
    os.makedirs(os.path.dirname(registro.caminho_original), exist_ok=True)
    caminho_lixeira = os.path.join(settings.LIXEIRA_DIR, registro.nome_na_lixeira)
    shutil.move(caminho_lixeira, registro.caminho_original)
    registro.delete()


def excluir_itens_lixeira(usuario, itens):
    os.makedirs(settings.LIXEIRA_DIR, exist_ok=True)
    sucessos = 0
    erros = 0
    for caminho_item in itens:
        try:
            caminho_item = validar_caminho_seguro(caminho_item)
            validar_acesso_ged(usuario, caminho_item)
            if caminho_item.casefold() == settings.LIXEIRA_DIR.casefold() or not os.path.exists(caminho_item):
                continue
            nome_base = os.path.basename(caminho_item)
            caminho_destino = os.path.join(settings.LIXEIRA_DIR, nome_base)
            if os.path.exists(caminho_destino):
                nome, extensao = os.path.splitext(nome_base)
                caminho_destino = os.path.join(
                    settings.LIXEIRA_DIR,
                    f'{nome}_{datetime.now():%Y%m%d_%H%M%S}{extensao}',
                )
            shutil.move(caminho_item, caminho_destino)
            try:
                RegistroLixeira.objects.create(
                    nome_na_lixeira=os.path.basename(caminho_destino),
                    caminho_original=caminho_item,
                    apagado_por=usuario,
                )
            except Exception:
                shutil.move(caminho_destino, caminho_item)
                raise
            LogAuditoria.objects.create(
                usuario=usuario,
                acao='EXCLUSAO_MUTIPLA',
                descricao=f'Item movido para a lixeira: {nome_base}',
                caminho_item=caminho_item,
            )
            sucessos += 1
        except Exception:
            erros += 1
            logger.exception('Falha ao mover item para a lixeira: %s', caminho_item)
    return sucessos, erros


def esvaziar_lixeira(usuario):
    if not os.path.exists(settings.LIXEIRA_DIR):
        return None
    contador = 0
    for item in os.listdir(settings.LIXEIRA_DIR):
        caminho = os.path.join(settings.LIXEIRA_DIR, item)
        validar_caminho_seguro(caminho)
        if os.path.isfile(caminho) or os.path.islink(caminho):
            os.unlink(caminho)
        elif os.path.isdir(caminho):
            shutil.rmtree(caminho)
        contador += 1
    if contador:
        LogAuditoria.objects.create(
            usuario=usuario,
            acao='APAGAR',
            descricao=f'Lixeira esvaziada completamente ({contador} itens removidos).',
            caminho_item=settings.LIXEIRA_DIR,
        )
    return contador
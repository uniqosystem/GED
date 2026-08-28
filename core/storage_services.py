import os

from django.conf import settings
from django.core.exceptions import ValidationError

from .file_validation import validar_upload
from .file_services import secure_filename, validar_acesso_ged, validar_caminho_seguro, validar_nome_seguro
from .models import LogAuditoria


def upload_multiplo_permitido(caminho_atual):
    caminho_normalizado = os.path.normcase(os.path.normpath(caminho_atual or ''))
    base_ged = os.path.normcase(os.path.normpath(settings.GED_BASE_DIR))
    raizes_bloqueadas = {
        os.path.normcase(os.path.join(base_ged, 'PESSOA FISICA')),
        os.path.normcase(os.path.join(base_ged, 'PESSOA JURIDICA')),
        os.path.normcase(os.path.join(base_ged, 'setores')),
    }
    return caminho_normalizado not in raizes_bloqueadas


def criar_subpasta_ged(usuario, caminho_atual, nome_pasta_input):
    caminho_seguro = validar_caminho_seguro(caminho_atual)
    validar_acesso_ged(usuario, caminho_seguro)
    nome_pasta = os.path.basename(nome_pasta_input.strip())
    if not nome_pasta:
        raise ValidationError('O nome da pasta é inválido.')
    validar_nome_seguro(nome_pasta, eh_arquivo=False)

    caminho_nova_pasta = os.path.join(caminho_seguro, nome_pasta)
    if os.path.exists(caminho_nova_pasta):
        return False, nome_pasta
    os.makedirs(caminho_nova_pasta)
    return True, nome_pasta


def salvar_upload_ged(usuario, arquivo, caminho_destino):
    caminho_destino = validar_caminho_seguro(caminho_destino)
    validar_acesso_ged(usuario, caminho_destino)
    validar_upload(arquivo)
    if not os.path.isdir(caminho_destino):
        raise ValidationError('Diretório de destino inválido.')

    nome_seguro = secure_filename(os.path.basename(arquivo.name))
    if not nome_seguro:
        raise ValidationError('Nome de arquivo inválido.')
    validar_nome_seguro(nome_seguro, eh_arquivo=True)
    caminho_final = os.path.join(caminho_destino, nome_seguro)
    try:
        with open(caminho_final, 'xb') as destination:
            for chunk in arquivo.chunks():
                destination.write(chunk)
    except FileExistsError as exc:
        raise ValidationError(f"O arquivo '{nome_seguro}' já existe nesta pasta.") from exc
    except Exception:
        if os.path.exists(caminho_final):
            os.remove(caminho_final)
        raise

    LogAuditoria.objects.create(usuario=usuario, acao='UPLOAD', descricao=nome_seguro, caminho_item=caminho_final)
    return nome_seguro, caminho_final
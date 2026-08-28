import os
import zipfile

from django.conf import settings
from django.core.exceptions import ValidationError


def validar_upload(arquivo):
    tamanho = getattr(arquivo, 'size', None)
    if tamanho is None or tamanho > settings.UPLOAD_MAX_SIZE:
        limite_mb = settings.UPLOAD_MAX_SIZE / (1024 * 1024)
        raise ValidationError(f'O arquivo excede o limite de {limite_mb:g} MB.')

    extensao = os.path.splitext(arquivo.name)[1].lower()
    extensoes_permitidas = {
        item.lower() if item.startswith('.') else f'.{item.lower()}'
        for item in settings.UPLOAD_ALLOWED_EXTENSIONS
    }
    if extensao not in extensoes_permitidas:
        raise ValidationError('A extensão do arquivo não é permitida.')

    tipo = getattr(arquivo, 'content_type', None)
    tipos_por_extensao = {
        '.pdf': {'application/pdf'},
        '.doc': {'application/msword', 'application/octet-stream'},
        '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/octet-stream'},
        '.xls': {'application/vnd.ms-excel', 'application/octet-stream'},
        '.xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/octet-stream'},
        '.csv': {'text/csv', 'text/plain', 'application/vnd.ms-excel'},
        '.txt': {'text/plain'},
        '.png': {'image/png'},
        '.jpg': {'image/jpeg'},
        '.jpeg': {'image/jpeg'},
        '.gif': {'image/gif'},
    }
    tipos_permitidos = tipos_por_extensao.get(extensao)
    if tipo and tipos_permitidos and tipo.lower() not in tipos_permitidos:
        raise ValidationError('O tipo MIME do arquivo não corresponde à extensão.')

    posicao_atual = arquivo.tell() if hasattr(arquivo, 'tell') else 0
    try:
        inicio = arquivo.read(16)
        arquivo.seek(0)
        if extensao == '.pdf' and not inicio.startswith(b'%PDF-'):
            raise ValidationError('O conteúdo não corresponde a um arquivo PDF válido.')
        if extensao == '.png' and inicio[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValidationError('O conteúdo não corresponde a uma imagem PNG válida.')
        if extensao in {'.jpg', '.jpeg'} and not inicio.startswith(b'\xff\xd8\xff'):
            raise ValidationError('O conteúdo não corresponde a uma imagem JPEG válida.')
        if extensao == '.gif' and inicio[:6] not in {b'GIF87a', b'GIF89a'}:
            raise ValidationError('O conteúdo não corresponde a uma imagem GIF válida.')
        if extensao in {'.doc', '.xls'} and inicio[:8] != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
            raise ValidationError('O conteúdo não corresponde a um arquivo Office válido.')
        if extensao in {'.docx', '.xlsx'}:
            if not zipfile.is_zipfile(arquivo):
                raise ValidationError('O conteúdo não corresponde a um arquivo Office válido.')
            arquivo.seek(0)
            with zipfile.ZipFile(arquivo) as pacote:
                contem_macro = any(
                    nome.casefold().endswith('/vbaproject.bin')
                    or nome.casefold() == 'vbaproject.bin'
                    for nome in pacote.namelist()
                )
            if contem_macro:
                raise ValidationError('Arquivos Office com macros não são permitidos.')
        if extensao in {'.csv', '.txt'} and b'\x00' in arquivo.read(4096):
            raise ValidationError('O conteúdo não corresponde a um arquivo de texto válido.')
    finally:
        arquivo.seek(posicao_atual)

    return arquivo
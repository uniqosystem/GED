"""Utilitarios de upload e anexos da tramitacao."""

from core.file_validation import validar_upload

from .models import AnexoTramitacao


def resolver_arquivos_upload(files, campos):
    for campo in campos:
        arquivos = files.getlist(campo)
        if arquivos:
            return arquivos
    return []


def adicionar_anexos_tramitacao(tramitacao, historico, arquivos):
    for arquivo in arquivos:
        validar_upload(arquivo)
        AnexoTramitacao.objects.create(
            tramitacao=tramitacao,
            historico=historico,
            arquivo=arquivo,
        )

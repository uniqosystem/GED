"""Regras de processamento e geracao de lotes e-Carta."""

from datetime import datetime
from io import StringIO

import pandas as pd
from django.core.files.base import ContentFile
from django.db import transaction

from core.file_validation import validar_upload
from core.models import LogAuditoria

from .models import ConfiguracaoEcarta, LoteEcarta

CARTAO_POSTAGEM = "0077383354"
CONTRATO_FIXO = "55944"
CONTRATO_COMPLETO = "9912590606"
COLUNAS_NECESSARIAS = [
    "NOME", "ENDEREÇO", "NÚM. ENDEREÇO", "END. COMPLEMENTO",
    "BAIRRO", "CIDADE", "UF", "CEP",
]


def _ler_planilha(arquivo_enviado):
    nome_arquivo = arquivo_enviado.name.lower()
    if nome_arquivo.endswith(('.xls', '.xlsx')):
        arquivo_enviado.seek(0)
        return pd.read_excel(
            arquivo_enviado,
            dtype=str,
            engine='openpyxl' if nome_arquivo.endswith('.xlsx') else 'xlrd',
        ).fillna('')

    sample = arquivo_enviado.read(4096).decode('latin1', errors='ignore')
    separador = ';' if ';' in sample else (',' if ',' in sample else '\t')
    arquivo_enviado.seek(0)
    conteudo_csv = arquivo_enviado.read().decode('latin1', errors='ignore')
    return pd.read_csv(
        StringIO(conteudo_csv),
        sep=separador,
        encoding='latin1',
        dtype=str,
        quotechar='"',
        engine='python',
    ).fillna('')


def gerar_lote(arquivo_enviado):
    validar_upload(arquivo_enviado)
    dataframe = _ler_planilha(arquivo_enviado)
    dataframe.columns = [
        str(col).strip().upper().replace('"', '').replace("'", '')
        for col in dataframe.columns
    ]
    dataframe = dataframe.astype(str).apply(lambda coluna: coluna.str.strip())

    faltando = [coluna for coluna in COLUNAS_NECESSARIAS if coluna not in dataframe.columns]
    if faltando:
        raise ValueError(f'As colunas {faltando} não foram encontradas no arquivo.')

    config, _ = ConfiguracaoEcarta.objects.get_or_create(
        id=1,
        defaults={'ultimo_lote': 15},
    )
    config.ultimo_lote += 1
    numero_lote = str(config.ultimo_lote)
    config.save()

    indices_colunas = {nome: indice for indice, nome in enumerate(dataframe.columns)}
    linhas_servico = []
    for indice, row in enumerate(dataframe.itertuples(index=False, name=None), start=1):
        coc = str(indice)
        nome_pdf = f'e-Carta_{CONTRATO_FIXO}_{numero_lote}_{coc}_1_complementar.pdf'
        campos = [
            '1', coc, numero_lote, CARTAO_POSTAGEM, CONTRATO_COMPLETO,
            '', 'N', '', 'S', nome_pdf,
            row[indices_colunas['NOME']], row[indices_colunas['ENDEREÇO']],
            row[indices_colunas['NÚM. ENDEREÇO']], row[indices_colunas['END. COMPLEMENTO']],
            row[indices_colunas['BAIRRO']], row[indices_colunas['CIDADE']],
            row[indices_colunas['UF']], row[indices_colunas['CEP']],
        ]
        linhas_servico.append('|'.join(campos))

    conteudo_servico = '\n'.join(linhas_servico)
    timestamp = datetime.now().strftime('%d%m%Y%H%M%S')
    nome_resposta_txt = f'e-Carta_{CONTRATO_FIXO}_{numero_lote}_Resposta{timestamp}.txt'
    return {
        'lote': numero_lote,
        'conteudo_servico': conteudo_servico,
        'conteudo_resposta': f'1|{numero_lote}|A\n',
        'nome_resposta': nome_resposta_txt,
    }


@transaction.atomic
def persistir_lote(resultado, usuario):
    lote = LoteEcarta.objects.create(
        numero_lote=resultado['lote'],
        criado_por=usuario,
    )
    try:
        lote.arquivo_servico.save(
            f'e-Carta_{CONTRATO_FIXO}_{lote.numero_lote}_servico.txt',
            ContentFile(resultado['conteudo_servico'].encode('utf-8')),
            save=False,
        )
        lote.arquivo_resposta.save(
            resultado['nome_resposta'],
            ContentFile(resultado['conteudo_resposta'].encode('utf-8')),
            save=False,
        )
        lote.save(update_fields=['arquivo_servico', 'arquivo_resposta'])
        LogAuditoria.objects.create(
            usuario=usuario,
            acao='GERAR_ECARTA',
            descricao=f'Lote e-Carta {lote.numero_lote} gerado',
            caminho_item=f'lotes/{lote.numero_lote}',
        )
    except Exception:
        if lote.arquivo_servico:
            lote.arquivo_servico.delete(save=False)
        if lote.arquivo_resposta:
            lote.arquivo_resposta.delete(save=False)
        lote.delete()
        raise
    return lote

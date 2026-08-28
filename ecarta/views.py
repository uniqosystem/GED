import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .download_views import baixar_resposta, baixar_servico
from .services import CONTRATO_FIXO, gerar_lote

logger = logging.getLogger(__name__)

@login_required
def gerar_ecarta(request):
    if request.method == 'POST':
        arquivo_enviado = request.FILES.get('arquivo_csv')

        if not arquivo_enviado:
            messages.error(request, "Por favor, selecione o arquivo (.xls ou .csv).")
            return redirect('gerar_ecarta')

        try:
            lote = gerar_lote(arquivo_enviado)

            # Salva na sessão para permitir o download imediato nos botões
            request.session['ecarta_servico'] = lote['conteudo_servico']
            request.session['ecarta_resposta'] = lote['conteudo_resposta']
            request.session['ecarta_lote'] = lote['lote']
            request.session['ecarta_nome_resposta'] = lote['nome_resposta']

            messages.success(request, f"Lote {lote['lote']} gerado com sucesso! Clique abaixo para baixar os arquivos.")
            return render(request, 'ecarta/gerar.html', {'gerado': True, 'lote': lote['lote']})

        except Exception:
            logger.exception('Falha ao processar arquivo e-Carta')
            messages.error(request, "Não foi possível processar o arquivo enviado.")
            return redirect('gerar_ecarta')

    return render(request, 'ecarta/gerar.html', {'gerado': False})


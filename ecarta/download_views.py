import io
import zipfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect

from .services import CONTRATO_FIXO


@login_required
def baixar_servico(request):
    conteudo = request.session.get('ecarta_servico')
    lote = request.session.get('ecarta_lote', '000000')
    if not conteudo:
        messages.error(request, "Nenhum arquivo de serviço disponível. Gere o lote primeiro.")
        return redirect('gerar_ecarta')

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f"e-Carta_{CONTRATO_FIXO}_{lote}_servico.txt", conteudo)
    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="e-Carta_{CONTRATO_FIXO}_{lote}_servico.zip"'
    return response


@login_required
def baixar_resposta(request):
    conteudo = request.session.get('ecarta_resposta')
    lote = request.session.get('ecarta_lote', '000000')
    nome_txt = request.session.get('ecarta_nome_resposta', 'resposta.txt')
    if not conteudo:
        messages.error(request, "Nenhum arquivo de resposta disponível. Gere o lote primeiro.")
        return redirect('gerar_ecarta')

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(nome_txt, conteudo)
    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="e-Carta_{CONTRATO_FIXO}_{lote}_resposta.zip"'
    return response
import mimetypes

from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe

from eventos.models import Certificado, Evento
from eventos.permissions import pode_gerenciar_eventos
from ponto.models import Contracheque, Ocorrencia
from tramitacao.models import AnexoHistorico, AnexoTramitacao
from tramitacao.permissions import usuario_tem_acesso_tramitacao
from ponto.permissions import is_ponto_rh


def _arquivo_evento_publico(nome):
    if '/imagens/' not in nome or not nome.startswith('eventos/'):
        return None
    return Evento.objects.filter(imagem=nome).exclude(status='RASCUNHO').first()


def _arquivo_tramitacao_autorizado(usuario, nome):
    for anexo in AnexoTramitacao.objects.filter(arquivo=nome).select_related('tramitacao'):
        if usuario_tem_acesso_tramitacao(usuario, anexo.tramitacao):
            return anexo.arquivo

    anexos_historico = AnexoHistorico.objects.filter(arquivo=nome).select_related(
        'historico__tramitacao'
    )
    for anexo in anexos_historico:
        tramitacao = getattr(anexo.historico, 'tramitacao', None)
        if tramitacao and usuario_tem_acesso_tramitacao(usuario, tramitacao):
            return anexo.arquivo
    return None


@require_safe
def private_media(request, path):
    nome = path.replace('\\', '/')
    if nome.startswith('eventos/') and '/imagens/' in nome:
        evento = _arquivo_evento_publico(nome)
        if evento and evento.imagem:
            arquivo = evento.imagem
            publico = True
        else:
            raise Http404
    elif request.user.is_authenticated:
        arquivo = _arquivo_tramitacao_autorizado(request.user, nome)
        if arquivo is None and nome.startswith('eventos/') and '/certificados/' in nome:
            certificado = Certificado.objects.filter(arquivo=nome).select_related(
                'inscricao__evento'
            ).first()
            if certificado and pode_gerenciar_eventos(request.user):
                arquivo = certificado.arquivo
        if arquivo is None and nome.startswith('contracheques/'):
            contracheque = Contracheque.objects.filter(arquivo=nome).select_related('usuario').first()
            if contracheque and (
                contracheque.usuario_id == request.user.id or is_ponto_rh(request.user)
            ):
                arquivo = contracheque.arquivo
        if arquivo is None and nome.startswith('atestados/'):
            ocorrencia = Ocorrencia.objects.filter(anexo=nome).select_related('usuario').first()
            if ocorrencia and (
                ocorrencia.usuario_id == request.user.id or is_ponto_rh(request.user)
            ):
                arquivo = ocorrencia.anexo
        if arquivo is None:
            raise Http404
        publico = False
    else:
        raise Http404

    try:
        arquivo_aberto = arquivo.open('rb')
    except (OSError, ValueError):
        raise Http404 from None

    content_type = mimetypes.guess_type(arquivo.name)[0] or 'application/octet-stream'
    response = FileResponse(
        arquivo_aberto,
        as_attachment=not publico,
        filename=arquivo.name.rsplit('/', 1)[-1],
        content_type=content_type,
    )
    response['X-Content-Type-Options'] = 'nosniff'
    if not publico:
        response['Cache-Control'] = 'private, no-store'
    return response
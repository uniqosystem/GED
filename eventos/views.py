import logging

from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .forms import CampoInscricaoFormSet, EventoForm, InscricaoForm
from .models import Evento, Inscricao
from .permissions import exigir_gestor_eventos
from .services import confirmar_presencas, criar_inscricao, enviar_certificado, gerar_certificado, registrar_auditoria

logger = logging.getLogger(__name__)


def lista_eventos(request):
	for evento in Evento.objects.filter(status='PUBLICADO'):
		evento.atualizar_status_automatico()
	eventos = Evento.objects.exclude(status='RASCUNHO')
	return render(request, 'eventos/lista.html', {'eventos': eventos})


def detalhe_evento(request, slug):
	evento = get_object_or_404(Evento, slug=slug)
	evento.atualizar_status_automatico()
	if evento.status == 'RASCUNHO':
		raise Http404
	return render(request, 'eventos/detalhe.html', {'evento': evento})


def inscrever_evento(request, slug):
	evento = get_object_or_404(Evento, slug=slug, status='PUBLICADO')
	evento.atualizar_status_automatico()
	if not evento.inscricoes_abertas:
		return render(request, 'eventos/detalhe.html', {'evento': evento})

	form = InscricaoForm(request.POST or None, evento=evento)
	if request.method == 'POST' and form.is_valid():
		try:
			criar_inscricao(evento, form.cleaned_data, form.respostas_adicionais())
		except ValidationError as erro:
			form.add_error(None, erro.message)
		else:
			return redirect('eventos:inscricao_sucesso', slug=evento.slug)

	return render(request, 'eventos/inscricao.html', {'evento': evento, 'form': form})


def inscricao_sucesso(request, slug):
	evento = get_object_or_404(Evento.objects.exclude(status='RASCUNHO'), slug=slug)
	return render(request, 'eventos/inscricao_sucesso.html', {'evento': evento})


def _slug_disponivel(titulo, evento=None):
	base = slugify(titulo) or 'evento'
	slug = base
	contador = 2
	while Evento.objects.filter(slug=slug).exclude(pk=getattr(evento, 'pk', None)).exists():
		slug = f'{base}-{contador}'
		contador += 1
	return slug


@login_required
@exigir_gestor_eventos
def gestao_lista(request):
	eventos = Evento.objects.select_related('criado_por').all()
	for evento in eventos:
		evento.atualizar_status_automatico()
	return render(request, 'eventos/gestao_lista.html', {'eventos': eventos})


@login_required
@exigir_gestor_eventos
def gestao_criar(request):
	evento = Evento(criado_por=request.user)
	form = EventoForm(request.POST or None, request.FILES or None, instance=evento)
	formset = CampoInscricaoFormSet(request.POST or None, instance=evento)
	if request.method == 'POST' and form.is_valid() and formset.is_valid():
		with transaction.atomic():
			evento = form.save(commit=False)
			evento.criado_por = request.user
			evento.slug = _slug_disponivel(evento.titulo)
			evento.save()
			formset.instance = evento
			formset.save()
			registrar_auditoria(request.user, 'CRIAR_EVENTO', f'Evento criado: {evento.titulo}')
		messages.success(request, 'Evento criado com sucesso.')
		return redirect('eventos:gestao_lista')

	return render(request, 'eventos/gestao_form.html', {
		'titulo_pagina': 'Criar evento',
		'form': form,
		'formset': formset,
	})


@login_required
@exigir_gestor_eventos
def gestao_editar(request, pk):
	evento = get_object_or_404(Evento, pk=pk)
	form = EventoForm(request.POST or None, request.FILES or None, instance=evento)
	formset = CampoInscricaoFormSet(request.POST or None, instance=evento)
	if request.method == 'POST' and form.is_valid() and formset.is_valid():
		with transaction.atomic():
			evento = form.save(commit=False)
			evento.save()
			formset.save()
			registrar_auditoria(request.user, 'EDITAR_EVENTO', f'Evento editado: {evento.titulo}')
		messages.success(request, 'Evento atualizado com sucesso.')
		return redirect('eventos:gestao_lista')

	return render(request, 'eventos/gestao_form.html', {
		'titulo_pagina': 'Editar evento',
		'form': form,
		'formset': formset,
		'evento': evento,
	})


@login_required
@exigir_gestor_eventos
def gestao_inscricoes(request, pk):
	evento = get_object_or_404(Evento, pk=pk)
	termo = request.GET.get('q', '').strip()
	inscricoes = evento.inscricoes.filter(cancelado_em__isnull=True)
	if termo:
		inscricoes = inscricoes.filter(
			Q(nome__icontains=termo)
			| Q(cpf__icontains=termo)
			| Q(email__icontains=termo)
		)
	return render(request, 'eventos/gestao_inscricoes.html', {
		'evento': evento,
		'inscricoes': inscricoes,
		'termo': termo,
	})


@login_required
@exigir_gestor_eventos
def gestao_presencas(request, pk):
	evento = get_object_or_404(Evento, pk=pk)
	if request.method == 'POST':
		try:
			total = confirmar_presencas(
				evento,
				request.POST.getlist('inscricoes_ids'),
				request.user,
			)
		except ValidationError as erro:
			messages.error(request, erro.message)
		else:
			messages.success(request, f'{total} presença(s) confirmada(s).')
		return redirect('eventos:gestao_presencas', pk=evento.pk)

	inscricoes = evento.inscricoes.filter(cancelado_em__isnull=True).select_related('presenca')
	return render(request, 'eventos/gestao_presencas.html', {
		'evento': evento,
		'inscricoes': inscricoes,
	})


@login_required
@exigir_gestor_eventos
@require_POST
def gestao_gerar_certificado(request, pk):
	inscricao = get_object_or_404(Inscricao, pk=pk)
	try:
		certificado = gerar_certificado(inscricao)
		enviar_certificado(certificado)
	except ValidationError as erro:
		messages.error(request, erro.message)
	except Exception:
		logger.exception('Falha no envio manual do certificado da inscricao %s', inscricao.pk)
		messages.error(request, 'O certificado foi gerado, mas não foi possível enviá-lo por e-mail.')
	else:
		registrar_auditoria(request.user, 'GERAR_CERTIFICADO_EVENTO', f'Certificado solicitado para inscricao {inscricao.pk}')
		messages.success(request, 'Certificado gerado com sucesso.')
	return redirect('eventos:gestao_inscricoes', pk=inscricao.evento_id)

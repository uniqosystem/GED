from io import BytesIO

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import IntegrityError, transaction
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
import logging

from core.models import LogAuditoria

logger = logging.getLogger(__name__)


def registrar_auditoria(usuario, acao, descricao):
	try:
		LogAuditoria.objects.create(
			usuario=usuario,
			acao=acao,
			descricao=descricao[:255],
		)
	except Exception:
		logger.exception('Falha ao registrar auditoria de eventos: %s', acao)

from .models import Certificado, Evento, Inscricao, Presenca


@transaction.atomic
def criar_inscricao(evento, dados, respostas):
	evento = Evento.objects.select_for_update().get(pk=evento.pk)
	evento.atualizar_status_automatico()
	if not evento.inscricoes_abertas:
		raise ValidationError('As inscrições estão encerradas ou não há vagas disponíveis.')

	if evento.inscricoes.filter(cpf=dados['cpf'], cancelado_em__isnull=True).exists():
		raise ValidationError('Já existe uma inscrição ativa para este CPF neste evento.')

	try:
		inscricao = Inscricao.objects.create(
			evento=evento,
			nome=dados['nome'].strip(),
			cpf=dados['cpf'],
			email=dados['email'].strip().lower(),
			telefone=dados['telefone'].strip(),
			respostas=respostas,
			consentiu_lgpd=dados['consentiu_lgpd'],
		)
		evento.atualizar_status_automatico()
		registrar_auditoria(None, 'INSCRICAO_EVENTO', f'Inscricao publica no evento {evento.titulo}')
		return inscricao
	except IntegrityError as exc:
		raise ValidationError('Não foi possível concluir a inscrição. Tente novamente.') from exc


@transaction.atomic
def confirmar_presencas(evento, inscricoes_ids, usuario):
	evento = Evento.objects.select_for_update().get(pk=evento.pk)
	if evento.status != 'REALIZADO':
		raise ValidationError('Só é possível confirmar presenças após marcar o evento como realizado.')

	ids_confirmados = {str(inscricao_id) for inscricao_id in inscricoes_ids}
	inscricoes = Inscricao.objects.select_for_update().filter(
		evento=evento,
		cancelado_em__isnull=True,
	)
	agora = timezone.now()
	total_confirmados = 0
	ids_para_emitir = []
	for inscricao in inscricoes:
		presenca, _ = Presenca.objects.get_or_create(inscricao=inscricao)
		confirmada = str(inscricao.pk) in ids_confirmados
		if confirmada:
			presenca.confirmada = True
			presenca.confirmada_por = usuario
			presenca.confirmada_em = agora
			total_confirmados += 1
			ids_para_emitir.append(inscricao.pk)
		else:
			presenca.confirmada = False
			presenca.confirmada_por = None
			presenca.confirmada_em = None
		presenca.save(update_fields=['confirmada', 'confirmada_por', 'confirmada_em'])

	transaction.on_commit(lambda: emitir_certificados_confirmados(ids_para_emitir))
	registrar_auditoria(usuario, 'CONFIRMAR_PRESENCA_EVENTO', f'Presencas atualizadas no evento {evento.titulo}')

	return total_confirmados


@transaction.atomic
def gerar_certificado(inscricao):
	inscricao = Inscricao.objects.select_for_update().select_related('evento').get(pk=inscricao.pk)
	if not Presenca.objects.filter(inscricao=inscricao, confirmada=True).exists():
		raise ValidationError('O certificado só pode ser gerado após a confirmação da presença.')

	certificado, _ = Certificado.objects.get_or_create(inscricao=inscricao)
	if certificado.arquivo and certificado.gerado_em:
		return certificado

	buffer = BytesIO()
	pdf = canvas.Canvas(buffer, pagesize=A4)
	largura, altura = A4
	pdf.setTitle(f'Certificado - {inscricao.nome}')
	pdf.setStrokeColorRGB(0.05, 0.25, 0.45)
	pdf.setLineWidth(2)
	pdf.rect(1.2 * cm, 1.2 * cm, largura - 2.4 * cm, altura - 2.4 * cm)
	pdf.setFillColorRGB(0.05, 0.25, 0.45)
	pdf.setFont('Helvetica-Bold', 25)
	pdf.drawCentredString(largura / 2, altura - 4 * cm, 'CERTIFICADO')
	pdf.setFillColorRGB(0.15, 0.15, 0.15)
	pdf.setFont('Helvetica', 13)
	pdf.drawCentredString(largura / 2, altura - 6 * cm, 'Certificamos que')
	pdf.setFont('Helvetica-Bold', 20)
	pdf.drawCentredString(largura / 2, altura - 7.5 * cm, inscricao.nome)
	pdf.setFont('Helvetica', 12)

	texto = (
		f'CPF {inscricao.cpf}, participou do evento "{inscricao.evento.titulo}", '
		f'realizado em {inscricao.evento.data_evento.strftime("%d/%m/%Y")}, '
		f'com carga horária de {inscricao.evento.carga_horaria} horas, '
		f'em {inscricao.evento.local}.'
	)
	linhas = [texto[index:index + 95] for index in range(0, len(texto), 95)]
	y = altura - 10 * cm
	for linha in linhas:
		pdf.drawCentredString(largura / 2, y, linha)
		y -= 0.65 * cm

	pdf.setFont('Helvetica', 9)
	pdf.drawCentredString(largura / 2, 3.2 * cm, f'Código de validação: {certificado.codigo}')
	pdf.showPage()
	pdf.save()

	certificado.arquivo.save(
		f'certificado-{certificado.codigo}.pdf',
		ContentFile(buffer.getvalue()),
		save=False,
	)
	certificado.gerado_em = timezone.now()
	certificado.save(update_fields=['arquivo', 'gerado_em'])
	registrar_auditoria(None, 'GERAR_CERTIFICADO_EVENTO', f'Certificado gerado para inscricao {inscricao.pk}')
	return certificado


def enviar_certificado(certificado):
	if certificado.enviado_em:
		return certificado
	if not certificado.arquivo:
		raise ValidationError('O certificado ainda não possui um arquivo PDF.')

	try:
		with certificado.arquivo.open('rb') as arquivo:
			mensagem = EmailMessage(
				subject=f'Certificado - {certificado.inscricao.evento.titulo}',
				body=(
					f'Olá, {certificado.inscricao.nome}.\n\n'
					f'Seguimos com o certificado do evento {certificado.inscricao.evento.titulo}.'
				),
				from_email=None,
				to=[certificado.inscricao.email],
			)
			mensagem.attach(arquivo.name.rsplit('/', 1)[-1], arquivo.read(), 'application/pdf')
			mensagem.send(fail_silently=False)
	except Exception as exc:
		certificado.erro_envio = str(exc)
		certificado.save(update_fields=['erro_envio'])
		raise

	certificado.enviado_em = timezone.now()
	certificado.erro_envio = ''
	certificado.save(update_fields=['enviado_em', 'erro_envio'])
	registrar_auditoria(None, 'ENVIAR_CERTIFICADO_EVENTO', f'Certificado enviado para inscricao {certificado.inscricao_id}')
	return certificado


def emitir_certificado(inscricao):
	certificado = gerar_certificado(inscricao)
	try:
		enviar_certificado(certificado)
	except Exception:
		logger.exception('Falha ao enviar certificado da inscrição %s', inscricao.pk)
	return certificado


def emitir_certificados_confirmados(inscricoes_ids):
	for inscricao_id in inscricoes_ids:
		inscricao = Inscricao.objects.filter(pk=inscricao_id).first()
		if inscricao:
			emitir_certificado(inscricao)

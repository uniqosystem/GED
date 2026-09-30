import uuid
import posixpath

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from core.configured_storage import ConfiguredRootStorage

eventos_storage = ConfiguredRootStorage('EVENTOS_DIR')


def caminho_imagem_evento(instance, filename):
	slug = slugify(instance.slug or instance.titulo) or 'evento'
	return posixpath.join('eventos', f'{instance.pk}-{slug}', 'imagens', filename)


def caminho_certificado_evento(instance, filename):
	slug = slugify(instance.inscricao.evento.slug) or 'evento'
	return posixpath.join('eventos', f'{instance.inscricao.evento_id}-{slug}', 'certificados', filename)


class Evento(models.Model):
	STATUS_CHOICES = [
		('RASCUNHO', 'Rascunho'),
		('PUBLICADO', 'Publicado'),
		('ENCERRADO', 'Inscricoes encerradas'),
		('REALIZADO', 'Realizado'),
		('CANCELADO', 'Cancelado'),
	]

	titulo = models.CharField(max_length=200, verbose_name='Nome do Evento')
	slug = models.SlugField(max_length=220, unique=True)
	data_evento = models.DateField(verbose_name='Data do Evento')
	hora_inicio = models.TimeField(verbose_name='Horario de inicio')
	hora_fim = models.TimeField(null=True, blank=True, verbose_name='Horario de termino')
	local = models.CharField(max_length=255, verbose_name='Local')
	palestrantes = models.TextField(blank=True, verbose_name='Palestrantes')
	descricao = models.TextField(verbose_name='Descricao')
	regras = models.TextField(blank=True, verbose_name='Regras e restricoes')
	carga_horaria = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Carga horaria')
	imagem = models.FileField(storage=eventos_storage, upload_to=caminho_imagem_evento, null=True, blank=True)
	limite_inscricoes = models.PositiveIntegerField(verbose_name='Quantidade maxima de inscritos')
	inscricoes_encerram_em = models.DateTimeField(verbose_name='Limite de inscricao')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RASCUNHO')
	criado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='eventos_criados')
	criado_em = models.DateTimeField(auto_now_add=True)
	atualizado_em = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['data_evento', 'hora_inicio', 'titulo']
		verbose_name = 'Evento'
		verbose_name_plural = 'Eventos'

	def __str__(self):
		return self.titulo

	def clean(self):
		super().clean()
		if self.hora_fim and self.hora_fim <= self.hora_inicio:
			raise ValidationError({'hora_fim': 'O horario de termino deve ser posterior ao inicio.'})
		if self.inscricoes_encerram_em and self.data_evento and self.hora_inicio:
			data_limite = timezone.make_aware(
				timezone.datetime.combine(self.data_evento, self.hora_inicio),
				timezone.get_current_timezone(),
			)
			if self.inscricoes_encerram_em > data_limite:
				raise ValidationError({'inscricoes_encerram_em': 'O limite de inscricao deve ser anterior ao evento.'})

	@property
	def total_inscricoes_ativas(self):
		return self.inscricoes.filter(cancelado_em__isnull=True).count()

	@property
	def vagas_disponiveis(self):
		return max(self.limite_inscricoes - self.total_inscricoes_ativas, 0)

	@property
	def inscricoes_abertas(self):
		return (
			self.status == 'PUBLICADO'
			and timezone.now() <= self.inscricoes_encerram_em
			and self.vagas_disponiveis > 0
		)

	def atualizar_status_automatico(self):
		if self.status != 'PUBLICADO':
			return False
		if self.vagas_disponiveis > 0 and timezone.now() <= self.inscricoes_encerram_em:
			return False
		self.status = 'ENCERRADO'
		self.save(update_fields=['status', 'atualizado_em'])
		return True


class CampoInscricao(models.Model):
	evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='campos_adicionais')
	nome = models.CharField(max_length=100)
	chave = models.SlugField(max_length=100)
	obrigatorio = models.BooleanField(default=False)
	ordem = models.PositiveIntegerField(default=0)
	ativo = models.BooleanField(default=True)

	class Meta:
		ordering = ['ordem', 'id']
		constraints = [
			models.UniqueConstraint(fields=['evento', 'chave'], name='evento_campo_chave_unica'),
		]

	def __str__(self):
		return f'{self.evento} - {self.nome}'


class Inscricao(models.Model):
	evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name='inscricoes')
	nome = models.CharField(max_length=200)
	cpf = models.CharField(max_length=11)
	email = models.EmailField()
	telefone = models.CharField(max_length=30)
	respostas = models.JSONField(default=dict, blank=True)
	consentiu_lgpd = models.BooleanField(default=False)
	inscrito_em = models.DateTimeField(auto_now_add=True)
	cancelado_em = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['-inscrito_em']
		constraints = [
			models.UniqueConstraint(
				fields=['evento', 'cpf'],
				condition=Q(cancelado_em__isnull=True),
				name='inscricao_ativa_evento_cpf_unica',
			),
		]

	def __str__(self):
		return f'{self.nome} - {self.evento}'


class Presenca(models.Model):
	inscricao = models.OneToOneField(Inscricao, on_delete=models.CASCADE, related_name='presenca')
	confirmada = models.BooleanField(default=False)
	confirmada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
	confirmada_em = models.DateTimeField(null=True, blank=True)

	def __str__(self):
		return f'Presenca - {self.inscricao}'


class Certificado(models.Model):
	inscricao = models.OneToOneField(Inscricao, on_delete=models.PROTECT, related_name='certificado')
	codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	arquivo = models.FileField(storage=eventos_storage, upload_to=caminho_certificado_evento, null=True, blank=True)
	gerado_em = models.DateTimeField(null=True, blank=True)
	enviado_em = models.DateTimeField(null=True, blank=True)
	erro_envio = models.TextField(blank=True)

	def __str__(self):
		return f'Certificado {self.codigo}'

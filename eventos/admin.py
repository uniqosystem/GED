from django.contrib import admin

from .models import CampoInscricao, Certificado, Evento, Inscricao, Presenca


class CampoInscricaoInline(admin.TabularInline):
	model = CampoInscricao
	extra = 0


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
	list_display = (
		'titulo',
		'data_evento',
		'status',
		'limite_inscricoes',
		'total_inscricoes_ativas',
		'criado_por',
	)
	list_filter = ('status', 'data_evento')
	search_fields = ('titulo', 'local', 'palestrantes')
	prepopulated_fields = {'slug': ('titulo',)}
	inlines = [CampoInscricaoInline]


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
	list_display = ('nome', 'evento', 'email', 'cpf', 'inscrito_em', 'cancelado_em')
	list_filter = ('evento', 'inscrito_em', 'cancelado_em')
	search_fields = ('nome', 'cpf', 'email', 'evento__titulo')
	readonly_fields = ('inscrito_em',)


@admin.register(Presenca)
class PresencaAdmin(admin.ModelAdmin):
	list_display = ('inscricao', 'confirmada', 'confirmada_por', 'confirmada_em')
	list_filter = ('confirmada', 'confirmada_em')
	search_fields = ('inscricao__nome', 'inscricao__cpf', 'inscricao__evento__titulo')
	readonly_fields = ('confirmada_em',)


@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
	list_display = ('inscricao', 'codigo', 'gerado_em', 'enviado_em')
	search_fields = ('codigo', 'inscricao__nome', 'inscricao__cpf', 'inscricao__evento__titulo')
	readonly_fields = ('codigo', 'gerado_em', 'enviado_em')

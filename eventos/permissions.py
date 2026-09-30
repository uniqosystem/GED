import unicodedata

from django.contrib.auth.decorators import user_passes_test


SETOR_GESTOR_EVENTOS = 'CURSOS E EVENTOS'


def _normalizar_nome(nome):
	sem_acentos = unicodedata.normalize('NFKD', nome or '')
	sem_acentos = ''.join(
		caractere for caractere in sem_acentos
		if not unicodedata.combining(caractere)
	)
	return ' '.join(sem_acentos.upper().split())


def pode_gerenciar_eventos(user):
	if not user or not user.is_authenticated:
		return False
	if user.is_superuser:
		return True

	perfil = getattr(user, 'perfil', None)
	setor = getattr(perfil, 'setor', None)
	return bool(setor and _normalizar_nome(setor.nome) == SETOR_GESTOR_EVENTOS)


def exigir_gestor_eventos(view_func):
	return user_passes_test(
		pode_gerenciar_eventos,
		login_url='inicio',
	)(view_func)

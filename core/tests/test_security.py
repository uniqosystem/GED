from unittest.mock import patch
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import RequestFactory, TestCase, override_settings
from django.db import connection
from django.urls import reverse

from core.models import LogAuditoria, Setor
from core.views import por_pagina_seguro, url_retorno_segura
from ponto.models import Contracheque


class GedSecurityTests(TestCase):
	def setUp(self):
		self.setor = Setor.objects.create(nome='TI', caminho_rede='C:\\GED\\TI')
		self.usuario = User.objects.create_user('usuario', password='senha')
		self.usuario.perfil.setor = self.setor
		self.usuario.perfil.save()

	def test_midia_privada_exige_autorizacao_do_proprietario(self):
		with TemporaryDirectory() as media_dir:
			with override_settings(MEDIA_ROOT=media_dir):
				contracheque = Contracheque(usuario=self.usuario, mes=9, ano=2026)
				contracheque.arquivo.save('contracheque.pdf', ContentFile(b'dados privados'))
				url = reverse('private_media', kwargs={'path': contracheque.arquivo.name})

				self.assertEqual(self.client.get(url).status_code, 404)

				self.usuario.perfil.password_changed = True
				self.usuario.perfil.save(update_fields=['password_changed'])
				self.client.force_login(self.usuario)
				resposta = self.client.get(url)
				self.assertEqual(resposta.status_code, 200)
				self.assertEqual(b''.join(resposta.streaming_content), b'dados privados')
				self.assertEqual(resposta['Cache-Control'], 'private, no-store')

				outro_usuario = User.objects.create_user('outro_usuario', password='senha')
				outro_usuario.perfil.password_changed = True
				outro_usuario.perfil.save(update_fields=['password_changed'])
				self.client.force_login(outro_usuario)
				self.assertEqual(self.client.get(url).status_code, 404)

	def test_health_check_retorna_status_ok(self):
		response = self.client.get('/health/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {'status': 'ok'})

	def test_health_check_retorna_indisponivel_quando_banco_falha(self):
		with patch('core.views.connection.ensure_connection', side_effect=Exception):
			response = self.client.get('/health/')
		self.assertEqual(response.status_code, 503)
		self.assertEqual(response.json(), {'status': 'unhealthy'})

	def test_exportacao_auditoria_exige_superusuario(self):
		response = self.client.get('/auditoria/exportar/')
		self.assertEqual(response.status_code, 302)

		self.usuario.perfil.password_changed = True
		self.usuario.perfil.save(update_fields=['password_changed'])
		self.client.force_login(self.usuario)
		response = self.client.get('/auditoria/exportar/')
		self.assertEqual(response.status_code, 302)
		self.assertIn('/?next=/auditoria/exportar/', response.url)

		administrador = User.objects.create_superuser('administrador', password='senha')
		administrador.perfil.password_changed = True
		administrador.perfil.save(update_fields=['password_changed'])
		self.client.force_login(administrador)
		response = self.client.get('/auditoria/exportar/')
		self.assertEqual(response.status_code, 200)

	def test_url_retorno_rejeita_destino_externo(self):
		request = RequestFactory().get('/')
		self.assertEqual(
			url_retorno_segura(request, 'https://exemplo-invalido.test/', '/inicio/'),
			'/inicio/',
		)
		self.assertEqual(
			url_retorno_segura(request, '/busca/?crf=123', '/inicio/'),
			'/busca/?crf=123',
		)

	def test_endpoints_de_mutacao_rejeitam_get(self):
		self.usuario.perfil.password_changed = True
		self.usuario.perfil.save(update_fields=['password_changed'])
		self.client.force_login(self.usuario)

		for url in (
			'/renomear/', '/apagar/', '/navegar/excluir-multiplos-ajax/',
			'/upload-geral/', '/upload-multiplo-ajax/', '/criar-pasta/',
		):
			with self.subTest(url=url):
				self.assertEqual(self.client.get(url).status_code, 405)

	def test_por_pagina_rejeita_valores_invalidos(self):
		self.assertEqual(por_pagina_seguro('abc', 25), 25)
		self.assertEqual(por_pagina_seguro('0', 25), 1)
		self.assertEqual(por_pagina_seguro('-10', 25), 1)
		self.assertEqual(por_pagina_seguro('10', 25), 10)

	def test_logout_registra_apenas_um_log_de_auditoria(self):
		self.usuario.perfil.password_changed = True
		self.usuario.perfil.save(update_fields=['password_changed'])
		self.client.force_login(self.usuario)

		response = self.client.get('/logout/')

		self.assertEqual(response.status_code, 302)
		self.assertEqual(LogAuditoria.objects.filter(
			usuario=self.usuario, acao='LOGOUT',
		).count(), 1)

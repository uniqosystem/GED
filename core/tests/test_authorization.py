import os
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.conf import settings
from django.core import management
from django.test import TestCase

from core.models import LogAuditoria, Setor
from core.views import usuario_pode_acessar_caminho


class GedAuthorizationTests(TestCase):
	def setUp(self):
		self.setor = Setor.objects.create(nome='TI', caminho_rede='C:\\GED\\TI')
		self.outro_setor = Setor.objects.create(nome='Financeiro', caminho_rede='C:\\GED\\Financeiro')
		self.usuario = User.objects.create_user('usuario', password='senha')
		self.usuario.perfil.setor = self.setor
		self.usuario.perfil.save()

	def test_usuario_acessa_apenas_seu_setor(self):
		self.assertTrue(usuario_pode_acessar_caminho(
			self.usuario, os.path.join(settings.SETORES_BASE_DIR, 'TI', 'arquivo.pdf')
		))
		self.assertFalse(usuario_pode_acessar_caminho(
			self.usuario, os.path.join(settings.SETORES_BASE_DIR, 'Financeiro', 'arquivo.pdf')
		))

	def test_usuario_nao_acessa_pf_pj_sem_grupo_explicito(self):
		self.assertFalse(usuario_pode_acessar_caminho(
			self.usuario, os.path.join(settings.GED_BASE_DIR, 'PESSOA FISICA', '08360')
		))
		self.assertFalse(usuario_pode_acessar_caminho(
			self.usuario, os.path.join(settings.GED_BASE_DIR, 'PESSOA JURIDICA', '08360')
		))

	def test_grupo_explicito_libera_modulo_pf(self):
		grupo = Group.objects.create(name='GED_PESSOA_FISICA')
		self.usuario.groups.add(grupo)
		self.assertTrue(usuario_pode_acessar_caminho(
			self.usuario, os.path.join(settings.GED_BASE_DIR, 'PESSOA FISICA', '08360')
		))

	def test_comando_provisiona_grupos_e_atribui_usuario(self):
		management.call_command('configurar_grupos_ged', pf_users=self.usuario.username, verbosity=0)
		self.usuario.refresh_from_db()
		self.assertTrue(self.usuario.groups.filter(name=settings.GED_PF_GROUPS[0]).exists())

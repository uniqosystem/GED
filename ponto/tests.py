from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from pathlib import Path
from tempfile import TemporaryDirectory

from core.models import Perfil, Setor
from .models import RegistroPonto
from .permissions import is_ponto_rh


class PontoIntegrationTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='funcionario', password='senha-segura')
		perfil = Perfil.objects.get(user=self.user)
		perfil.password_changed = True
		perfil.save(update_fields=['password_changed'])

	def test_root_redirects_to_registration(self):
		response = self.client.get('/ponto/')

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response['Location'], reverse('registrar_ponto'))

	def test_registration_requires_ged_authentication(self):
		response = self.client.get(reverse('registrar_ponto'))

		self.assertRedirects(response, '/?next=/ponto/registrar/')

	def test_registration_uses_ged_user(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse('registrar_ponto'))
		registro = RegistroPonto.objects.create(usuario=self.user, tipo='ENTRADA')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(registro.usuario, self.user)

	def test_registration_shows_ged_user_and_sector(self):
		self.user.first_name = 'Teste CRF-PB'
		self.user.save(update_fields=['first_name'])
		perfil = Perfil.objects.get(user=self.user)
		perfil.setor = Setor.objects.create(nome='TI', caminho_rede='C:\\TI')
		perfil.save(update_fields=['setor'])
		self.client.force_login(self.user)

		response = self.client.get(reverse('registrar_ponto'))

		self.assertContains(response, 'Usuário: Teste CRF-PB')
		self.assertContains(response, 'Setor: TI')

	@override_settings(PONTO_RH_GROUPS=['DEPARTAMENTO PESSOAL'])
	def test_department_personnel_group_can_manage_point(self):
		grupo = Group.objects.create(name='Departamento Pessoal')
		self.user.groups.add(grupo)

		self.assertTrue(is_ponto_rh(self.user))

	def test_regular_user_cannot_manage_point(self):
		self.assertFalse(is_ponto_rh(self.user))

	def test_regular_user_cannot_access_rh_panel(self):
		self.client.force_login(self.user)

		response = self.client.get(reverse('painel_rh'))

		self.assertRedirects(response, '/?next=/ponto/rh/')

	@override_settings(PONTO_RH_GROUPS=['DEPARTAMENTO PESSOAL'])
	def test_department_personnel_group_can_access_rh_panel(self):
		grupo = Group.objects.create(name='Departamento Pessoal')
		self.user.groups.add(grupo)
		self.client.force_login(self.user)

		response = self.client.get(reverse('painel_rh'))

		self.assertEqual(response.status_code, 200)

	def test_superuser_can_manage_point(self):
		self.user.is_superuser = True
		self.user.save(update_fields=['is_superuser'])

		self.assertTrue(is_ponto_rh(self.user))

	def test_export_report_is_saved_in_ponto_directory(self):
		self.user.is_staff = True
		self.user.save(update_fields=['is_staff'])
		RegistroPonto.objects.create(usuario=self.user, tipo='ENTRADA')

		with TemporaryDirectory() as diretorio:
			with override_settings(PONTO_DIR=diretorio):
				self.client.force_login(self.user)
				response = self.client.get(reverse('exportar_ponto'))

			arquivos = list(Path(diretorio).glob('*.xlsx'))

		self.assertEqual(response.status_code, 200)
		self.assertEqual(len(arquivos), 1)

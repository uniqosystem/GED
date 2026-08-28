from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Setor


class PasswordChangeTests(TestCase):
	def setUp(self):
		self.setor = Setor.objects.create(nome='TI', caminho_rede='C:\\GED\\TI')
		self.novo_usuario = User.objects.create_user('novousuario', password='senha_padrao')
		self.novo_usuario.perfil.setor = self.setor
		self.novo_usuario.perfil.password_changed = False
		self.novo_usuario.perfil.save()
		self.usuario_ativo = User.objects.create_user('usuarioativo', password='senha_padrao')
		self.usuario_ativo.perfil.setor = self.setor
		self.usuario_ativo.perfil.password_changed = True
		self.usuario_ativo.perfil.save()

	def test_novo_usuario_login_redireciona_para_change_password(self):
		response = self.client.post('/', {'username': 'novousuario', 'password': 'senha_padrao'}, follow=False)
		self.assertEqual(response.status_code, 302)
		self.assertIn('/alterar-senha/', response.url)

	def test_novo_usuario_bloqueado_de_acessar_inicio_sistema(self):
		self.client.login(username='novousuario', password='senha_padrao')
		response = self.client.get('/inicio/', follow=False)
		self.assertEqual(response.status_code, 302)
		self.assertIn('/alterar-senha/', response.url)

	def test_usuario_com_senha_alterada_nao_bloqueado(self):
		self.client.login(username='usuarioativo', password='senha_padrao')
		response = self.client.get('/inicio/', follow=False)
		self.assertEqual(response.status_code, 200)

	def test_usuario_com_senha_alterada_acessa_change_password_e_eh_redirecionado(self):
		self.client.login(username='usuarioativo', password='senha_padrao')
		response = self.client.get('/alterar-senha/', follow=False)
		self.assertEqual(response.status_code, 302)
		self.assertIn('/inicio/', response.url)

	def test_logout_antes_de_alterar_senha_force_proxima_alteracao(self):
		self.client.login(username='novousuario', password='senha_padrao')
		self.novo_usuario.perfil.refresh_from_db()
		self.assertFalse(self.novo_usuario.perfil.password_changed)
		self.client.logout()
		response = self.client.post('/', {'username': 'novousuario', 'password': 'senha_padrao'}, follow=False)
		self.assertEqual(response.status_code, 302)
		self.assertIn('/alterar-senha/', response.url)

	def test_novo_usuario_pode_acessar_formulario_mudanca_senha(self):
		self.client.login(username='novousuario', password='senha_padrao')
		response = self.client.get('/alterar-senha/', follow=False)
		if response.status_code == 200:
			self.assertIn('Alterar Senha', response.content.decode())

	def test_alterar_senha_rejeita_senha_comum(self):
		self.assertTrue(self.client.login(username='novousuario', password='senha_padrao'))
		response = self.client.post('/alterar-senha/', {'senha_atual': 'senha_padrao', 'senha_nova': 'password', 'senha_confirmacao': 'password'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Esta senha é muito comum')
		self.novo_usuario.refresh_from_db()
		self.assertTrue(self.novo_usuario.check_password('senha_padrao'))

	def test_alterar_senha_rejeita_senha_semelhante_ao_usuario(self):
		self.assertTrue(self.client.login(username='novousuario', password='senha_padrao'))
		response = self.client.post('/alterar-senha/', {'senha_atual': 'senha_padrao', 'senha_nova': 'novousuario123', 'senha_confirmacao': 'novousuario123'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'muito parecida com usuário')

	def test_alterar_senha_nao_exibe_detalhes_da_excecao(self):
		self.assertTrue(self.client.login(username='novousuario', password='senha_padrao'))
		with patch.object(User, 'save', side_effect=RuntimeError('detalhe interno do banco')) as mock_save:
			response = self.client.post('/alterar-senha/', {'senha_atual': 'senha_padrao', 'senha_nova': 'UmaSenhaForte!2026', 'senha_confirmacao': 'UmaSenhaForte!2026'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Não foi possível alterar sua senha. Tente novamente.')
		self.assertNotContains(response, 'detalhe interno do banco')
		mock_save.assert_called_once()

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Setor


class PerfilUsuarioTests(TestCase):
    def setUp(self):
        setor = Setor.objects.create(nome='Administrativo', caminho_rede='C:\\GED\\Administrativo')
        self.usuario = User.objects.create_user(
            'perfil_teste',
            password='senha-segura-123',
            first_name='Ana',
            email='ana@example.com',
        )
        self.usuario.perfil.setor = setor
        self.usuario.perfil.password_changed = True
        self.usuario.perfil.save(update_fields=['setor', 'password_changed'])
        self.url = reverse('perfil_usuario')

    def test_perfil_exige_autenticacao(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/?next=/perfil/', response.url)

    def test_perfil_exibe_dados_e_atualiza_contato(self):
        self.client.force_login(self.usuario)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Administrativo')

        response = self.client.post(self.url, {
            'first_name': 'Ana Maria',
            'last_name': 'Silva',
            'email': 'ana.maria@example.com',
        })

        self.assertRedirects(response, self.url)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, 'Ana Maria')
        self.assertEqual(self.usuario.last_name, 'Silva')
        self.assertEqual(self.usuario.email, 'ana.maria@example.com')
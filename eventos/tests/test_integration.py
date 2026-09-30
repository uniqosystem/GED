from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Setor


class EventosIntegrationTests(TestCase):
    def setUp(self):
        self.setor_eventos = Setor.objects.create(
            nome='Cursos e Eventos',
            caminho_rede='C:\\GED\\Cursos e Eventos',
        )
        self.outro_setor = Setor.objects.create(
            nome='Administrativo',
            caminho_rede='C:\\GED\\Administrativo',
        )

    def criar_usuario(self, username, setor):
        usuario = User.objects.create_user(username, password='senha')
        usuario.perfil.setor = setor
        usuario.perfil.password_changed = True
        usuario.perfil.save(update_fields=['setor', 'password_changed'])
        return usuario

    def test_login_exibe_carrossel_publico_de_eventos(self):
        resposta = self.client.get(reverse('inicio'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Eventos CRF-PB')
        self.assertContains(resposta, reverse('eventos:lista'))

    def test_sidebar_exibe_eventos_para_setor_autorizado(self):
        usuario = self.criar_usuario('gestor', self.setor_eventos)
        self.client.force_login(usuario)

        resposta = self.client.get(reverse('inicio_sistema'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, reverse('eventos:gestao_lista'))

    def test_sidebar_nao_exibe_eventos_para_outro_setor(self):
        usuario = self.criar_usuario('administrativo', self.outro_setor)
        self.client.force_login(usuario)

        resposta = self.client.get(reverse('inicio_sistema'))

        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, reverse('eventos:gestao_lista'))

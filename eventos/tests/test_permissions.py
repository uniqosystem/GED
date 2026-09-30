from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Setor

from eventos.permissions import pode_gerenciar_eventos


class EventosPermissionTests(TestCase):
    def setUp(self):
        self.setor_eventos = Setor.objects.create(
            nome='Cursos e Eventos',
            caminho_rede='C:\\GED\\Cursos e Eventos',
        )
        self.outro_setor = Setor.objects.create(
            nome='Administrativo',
            caminho_rede='C:\\GED\\Administrativo',
        )

    def criar_usuario_com_setor(self, username, setor):
        usuario = User.objects.create_user(username, password='senha')
        usuario.perfil.setor = setor
        usuario.perfil.save(update_fields=['setor'])
        return usuario

    def test_usuario_do_setor_cursos_e_eventos_pode_gerenciar(self):
        usuario = self.criar_usuario_com_setor('gestor', self.setor_eventos)

        self.assertTrue(pode_gerenciar_eventos(usuario))

    def test_comparacao_do_setor_ignora_acentos_e_espacos(self):
        setor = Setor.objects.create(
            nome='  CURSOS e EVENTOS ',
            caminho_rede='C:\\GED\\Cursos Eventos 2',
        )
        usuario = self.criar_usuario_com_setor('gestor_formatado', setor)

        self.assertTrue(pode_gerenciar_eventos(usuario))

    def test_usuario_de_outro_setor_nao_pode_gerenciar(self):
        usuario = self.criar_usuario_com_setor('outro_setor', self.outro_setor)

        self.assertFalse(pode_gerenciar_eventos(usuario))

    def test_usuario_staff_de_outro_setor_nao_pode_gerenciar(self):
        usuario = self.criar_usuario_com_setor('staff', self.outro_setor)
        usuario.is_staff = True
        usuario.save(update_fields=['is_staff'])

        self.assertFalse(pode_gerenciar_eventos(usuario))

    def test_superusuario_pode_gerenciar(self):
        usuario = User.objects.create_superuser('admin', 'admin@example.com', 'senha')

        self.assertTrue(pode_gerenciar_eventos(usuario))

    def test_usuario_anonimo_nao_pode_gerenciar(self):
        self.assertFalse(pode_gerenciar_eventos(None))

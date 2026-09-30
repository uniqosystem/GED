from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

SEED = {
    'ADMIN_SEED_USERNAME': 'admin',
    'ADMIN_SEED_EMAIL': 'admin@crfpb.org.br',
    'ADMIN_SEED_PASSWORD': 'Senha-Forte-Deploy-2026',
    'ADMIN_SEED_RESET_PASSWORD': False,
}


def executar():
    call_command('seed_admin', stdout=StringIO())


class SeedAdminTests(TestCase):
    @override_settings(ADMIN_SEED_USERNAME='', ADMIN_SEED_PASSWORD='')
    def test_sem_env_nao_cria_usuario(self):
        executar()
        self.assertFalse(User.objects.exists())

    @override_settings(**SEED)
    def test_cria_superusuario_com_troca_de_senha_obrigatoria(self):
        executar()
        admin = User.objects.get(username='admin')
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertEqual(admin.email, 'admin@crfpb.org.br')
        self.assertTrue(admin.check_password('Senha-Forte-Deploy-2026'))
        self.assertFalse(admin.perfil.password_changed)

    @override_settings(**SEED)
    def test_idempotente_nao_sobrescreve_senha_existente(self):
        executar()
        admin = User.objects.get(username='admin')
        admin.set_password('Senha-Trocada-Pelo-Admin-1')
        admin.save()
        admin.perfil.password_changed = True
        admin.perfil.save()

        executar()

        admin.refresh_from_db()
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(admin.check_password('Senha-Trocada-Pelo-Admin-1'))
        self.assertTrue(admin.perfil.password_changed)

    @override_settings(**SEED)
    def test_promove_usuario_existente(self):
        User.objects.create_user('admin', password='Outra-Senha-Qualquer-9')
        executar()
        admin = User.objects.get(username='admin')
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.check_password('Outra-Senha-Qualquer-9'))

    @override_settings(**{**SEED, 'ADMIN_SEED_RESET_PASSWORD': True})
    def test_reset_password_redefine_senha(self):
        User.objects.create_user('admin', password='Outra-Senha-Qualquer-9')
        executar()
        admin = User.objects.get(username='admin')
        self.assertTrue(admin.check_password('Senha-Forte-Deploy-2026'))
        self.assertFalse(admin.perfil.password_changed)

    @override_settings(**{**SEED, 'ADMIN_SEED_PASSWORD': '123'})
    def test_senha_fraca_falha(self):
        with self.assertRaises(CommandError):
            executar()
        self.assertFalse(User.objects.exists())

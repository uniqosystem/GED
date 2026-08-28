from django.contrib.auth.models import User
from django.test import TestCase

from core.audit_queries import filtrar_logs_auditoria
from core.models import LogAuditoria


class AuditQueryTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            'auditoria_teste', first_name='Ana', last_name='Silva', password='senha'
        )
        LogAuditoria.objects.create(
            usuario=self.usuario,
            acao='UPLOAD',
            descricao='Documento financeiro enviado',
            caminho_item='C:\\GED\\financeiro.pdf',
        )
        LogAuditoria.objects.create(
            usuario=self.usuario,
            acao='APAGAR',
            descricao='Documento financeiro removido',
            caminho_item='C:\\GED\\financeiro.pdf',
        )

    def test_filtra_por_busca_e_acao(self):
        logs = filtrar_logs_auditoria('Ana', 'APAGAR')

        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().descricao, 'Documento financeiro removido')

    def test_filtra_por_descricao(self):
        logs = filtrar_logs_auditoria('enviado')

        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().acao, 'UPLOAD')

    def test_view_de_auditoria_aplica_filtro_para_superusuario(self):
        administrador = User.objects.create_superuser('auditoria_admin', password='senha')
        administrador.perfil.password_changed = True
        administrador.perfil.save(update_fields=['password_changed'])
        self.client.force_login(administrador)

        resposta = self.client.get('/auditoria/?busca=enviado')

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Documento financeiro enviado')
        self.assertNotContains(resposta, 'Documento financeiro removido')
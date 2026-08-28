from django.contrib.auth.models import User
from django.test import Client, TestCase

from core.models import Setor

from .models import Tramitacao


class TramitationHttpTests(TestCase):
    def setUp(self):
        self.setor_origem = Setor.objects.create(nome='HTTP Origem', caminho_rede='C:\\GED\\HTTP Origem')
        self.setor_destino = Setor.objects.create(nome='HTTP Destino', caminho_rede='C:\\GED\\HTTP Destino')
        self.remetente = User.objects.create_user('http_remetente', password='senha')
        self.destinatario = User.objects.create_user('http_destinatario', password='senha')
        self.outro_usuario = User.objects.create_user('http_outro', password='senha')
        for usuario in (self.remetente, self.destinatario, self.outro_usuario):
            usuario.perfil.password_changed = True
            usuario.perfil.save()
        self.remetente.perfil.setor = self.setor_origem
        self.remetente.perfil.save()
        self.destinatario.perfil.setor = self.setor_destino
        self.destinatario.perfil.save()
        self.outro_usuario.perfil.setor = self.setor_destino
        self.outro_usuario.perfil.save()
        self.tramitacao = Tramitacao.objects.create(
            protocolo='HTTP-0001',
            criador=self.remetente,
            remetente=self.remetente,
            setor_origem=self.setor_origem,
            setor_destino=self.setor_destino,
            usuario_destino=self.destinatario,
            titulo='HTTP',
            despacho='Despacho HTTP',
            status='PENDENTE',
            aguardar_resposta=True,
        )

    def test_get_de_acao_mutavel_e_rejeitado(self):
        self.client.force_login(self.destinatario)
        response = self.client.get(f'/tramitacao/{self.tramitacao.id}/receber/')
        self.assertEqual(response.status_code, 405)

    def test_post_sem_csrf_e_rejeitado(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.destinatario)
        response = cliente.post(f'/tramitacao/{self.tramitacao.id}/receber/')
        self.assertEqual(response.status_code, 403)

    def test_usuario_destinatario_recebe_por_http(self):
        self.client.force_login(self.destinatario)
        response = self.client.post(f'/tramitacao/{self.tramitacao.id}/receber/')
        self.assertEqual(response.status_code, 302)
        self.tramitacao.refresh_from_db()
        self.assertEqual(self.tramitacao.status, 'RECEBIDO')

    def test_usuario_diferente_nao_recebe_por_http(self):
        self.client.force_login(self.outro_usuario)
        response = self.client.post(f'/tramitacao/{self.tramitacao.id}/receber/')
        self.assertEqual(response.status_code, 403)

    def test_resposta_final_atualiza_status_por_http(self):
        self.client.force_login(self.destinatario)
        self.client.post(f'/tramitacao/{self.tramitacao.id}/receber/')
        response = self.client.post(
            f'/tramitacao/{self.tramitacao.id}/responder/',
            {'despacho': 'Resposta HTTP', 'aguardar_resposta': ''},
        )
        self.assertEqual(response.status_code, 302)
        self.tramitacao.refresh_from_db()
        self.assertEqual(self.tramitacao.status, 'CONCLUIDO')

    def test_conclusao_sem_assinatura_exibe_modal_de_acao_bloqueada(self):
        self.tramitacao.exige_assinatura = True
        self.tramitacao.aguardar_resposta = False
        self.tramitacao.status = 'RECEBIDO'
        self.tramitacao.save(update_fields=['exige_assinatura', 'aguardar_resposta', 'status'])
        self.client.force_login(self.destinatario)
        response = self.client.post(
            f'/tramitacao/{self.tramitacao.id}/finalizar/',
            follow=True,
        )
        self.assertContains(response, 'modalAcaoBloqueada')
        self.assertContains(response, 'Ação Bloqueada')
        self.assertContains(response, 'A assinatura é obrigatória antes da conclusão.')

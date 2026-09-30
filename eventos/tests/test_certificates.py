from datetime import date, time, timedelta
import tempfile
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Setor
from eventos.models import Certificado, Evento, Inscricao, Presenca
from eventos.services import enviar_certificado, gerar_certificado


class EventosCertificateTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.override_media = override_settings(EVENTOS_DIR=self.media_dir.name)
        self.override_media.enable()
        self.addCleanup(self.override_media.disable)
        self.addCleanup(self.media_dir.cleanup)

        setor = Setor.objects.create(
            nome='Cursos e Eventos',
            caminho_rede='C:\\GED\\Cursos e Eventos',
        )
        self.gestor = User.objects.create_user('gestor', password='senha')
        self.gestor.perfil.setor = setor
        self.gestor.perfil.password_changed = True
        self.gestor.perfil.save(update_fields=['setor', 'password_changed'])
        self.evento = Evento.objects.create(
            titulo='Evento com certificado',
            slug='evento-com-certificado',
            data_evento=date.today(),
            hora_inicio=time(9, 0),
            hora_fim=time(12, 0),
            local='Auditorio CRF-PB',
            descricao='Descricao',
            carga_horaria='3.00',
            limite_inscricoes=10,
            inscricoes_encerram_em=timezone.now() - timedelta(days=1),
            status='REALIZADO',
            criado_por=self.gestor,
        )
        self.inscricao = Inscricao.objects.create(
            evento=self.evento,
            nome='Maria da Silva',
            cpf='52998224725',
            email='maria@example.com',
            telefone='83999990000',
            consentiu_lgpd=True,
        )

    def test_sem_presenca_confirmada_nao_gera_certificado(self):
        with self.assertRaisesMessage(ValidationError, 'confirmação da presença'):
            gerar_certificado(self.inscricao)

        self.assertFalse(Certificado.objects.exists())

    def test_presenca_confirmada_gera_pdf_com_codigo(self):
        Presenca.objects.create(
            inscricao=self.inscricao,
            confirmada=True,
            confirmada_por=self.gestor,
            confirmada_em=timezone.now(),
        )

        certificado = gerar_certificado(self.inscricao)

        self.assertEqual(Certificado.objects.count(), 1)
        self.assertTrue(certificado.arquivo.name.endswith('.pdf'))
        self.assertTrue(certificado.gerado_em)
        self.assertTrue(certificado.arquivo.read().startswith(b'%PDF-'))
        certificado.arquivo.close()

    def test_geracao_repetida_reutiliza_certificado(self):
        Presenca.objects.create(
            inscricao=self.inscricao,
            confirmada=True,
            confirmada_por=self.gestor,
            confirmada_em=timezone.now(),
        )

        primeiro = gerar_certificado(self.inscricao)
        segundo = gerar_certificado(self.inscricao)

        self.assertEqual(primeiro.pk, segundo.pk)
        self.assertEqual(primeiro.codigo, segundo.codigo)
        self.assertEqual(Certificado.objects.count(), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_envia_pdf_uma_unica_vez(self):
        Presenca.objects.create(
            inscricao=self.inscricao,
            confirmada=True,
            confirmada_por=self.gestor,
            confirmada_em=timezone.now(),
        )
        certificado = gerar_certificado(self.inscricao)

        enviar_certificado(certificado)
        enviar_certificado(certificado)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['maria@example.com'])
        self.assertEqual(mail.outbox[0].attachments[0][2], 'application/pdf')
        self.assertTrue(certificado.enviado_em)

    @patch('eventos.views.enviar_certificado', side_effect=RuntimeError('SMTP indisponivel'))
    def test_falha_de_smtp_no_endpoint_nao_retorna_erro_500(self, enviar_mock):
        Presenca.objects.create(
            inscricao=self.inscricao,
            confirmada=True,
            confirmada_por=self.gestor,
            confirmada_em=timezone.now(),
        )
        self.client.force_login(self.gestor)

        resposta = self.client.post(
            reverse('eventos:gestao_gerar_certificado', args=[self.inscricao.pk]),
        )

        self.assertRedirects(
            resposta,
            reverse('eventos:gestao_inscricoes', args=[self.evento.pk]),
        )
        enviar_mock.assert_called_once()

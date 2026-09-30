from datetime import date, time, timedelta
import tempfile

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from eventos.models import Evento


class EventosPublicTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('gestor', password='senha')
        limite = timezone.now() + timedelta(days=1)
        dados = {
            'data_evento': date.today() + timedelta(days=3),
            'hora_inicio': time(9, 0),
            'hora_fim': time(12, 0),
            'local': 'Auditorio CRF-PB',
            'descricao': 'Descricao do evento publicado.',
            'carga_horaria': '3.00',
            'limite_inscricoes': 50,
            'inscricoes_encerram_em': limite,
            'criado_por': self.usuario,
        }
        self.publicado = Evento.objects.create(
            titulo='Evento publicado',
            slug='evento-publicado',
            status='PUBLICADO',
            **dados,
        )
        Evento.objects.create(
            titulo='Evento rascunho',
            slug='evento-rascunho',
            status='RASCUNHO',
            **dados,
        )
        Evento.objects.create(
            titulo='Evento encerrado',
            slug='evento-encerrado',
            status='ENCERRADO',
            **dados,
        )

    def test_listagem_publica_exibe_todos_os_eventos_que_nao_sao_rascunho(self):
        resposta = self.client.get(reverse('eventos:lista'))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Evento publicado')
        self.assertContains(resposta, 'Evento encerrado')
        self.assertNotContains(resposta, 'Evento rascunho')

    def test_detalhe_publico_exibe_evento_publicado(self):
        resposta = self.client.get(reverse('eventos:detalhe', args=[self.publicado.slug]))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Auditorio CRF-PB')
        self.assertContains(resposta, '50')

    def test_detalhe_de_evento_rascunho_retorna_404(self):
        resposta = self.client.get(reverse('eventos:detalhe', args=['evento-rascunho']))

        self.assertEqual(resposta.status_code, 404)

    def test_detalhe_de_evento_encerrado_e_publico(self):
        resposta = self.client.get(reverse('eventos:detalhe', args=['evento-encerrado']))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Evento encerrado')

    def test_imagem_do_evento_publicado_usa_pasta_propria_e_e_publica(self):
        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(EVENTOS_DIR=media_dir):
                self.publicado.imagem.save('cartaz.png', ContentFile(b'imagem'))
                caminho = self.publicado.imagem.name
                self.assertTrue(caminho.startswith(
                    f'eventos/{self.publicado.pk}-evento-publicado/imagens/'
                ))

                resposta = self.client.get(reverse(
                    'private_media', kwargs={'path': caminho},
                ))
                conteudo = b''.join(resposta.streaming_content)
                resposta.close()

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta['Content-Disposition'].split(';')[0], 'inline')
        self.assertEqual(conteudo, b'imagem')

from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Setor
from eventos.models import Evento, Inscricao, Presenca


class EventosAttendanceTests(TestCase):
    def setUp(self):
        setor = Setor.objects.create(
            nome='Cursos e Eventos',
            caminho_rede='C:\\GED\\Cursos e Eventos',
        )
        self.gestor = User.objects.create_user('gestor', password='senha')
        self.gestor.perfil.setor = setor
        self.gestor.perfil.password_changed = True
        self.gestor.perfil.save(update_fields=['setor', 'password_changed'])
        self.evento = Evento.objects.create(
            titulo='Evento realizado',
            slug='evento-realizado',
            data_evento=date.today(),
            hora_inicio=time(9, 0),
            hora_fim=time(12, 0),
            local='Auditorio',
            descricao='Descricao',
            carga_horaria='3.00',
            limite_inscricoes=10,
            inscricoes_encerram_em=timezone.now() - timedelta(days=1),
            status='REALIZADO',
            criado_por=self.gestor,
        )
        self.inscricao_um = self.criar_inscricao('Pessoa Um', '52998224725')
        self.inscricao_dois = self.criar_inscricao('Pessoa Dois', '39053344705')
        self.url = reverse('eventos:gestao_presencas', args=[self.evento.pk])
        self.client.force_login(self.gestor)

    def criar_inscricao(self, nome, cpf):
        return Inscricao.objects.create(
            evento=self.evento,
            nome=nome,
            cpf=cpf,
            email=f'{cpf}@example.com',
            telefone='83999990000',
            consentiu_lgpd=True,
        )

    def test_gestor_confirma_presenca_e_registra_responsavel(self):
        resposta = self.client.post(self.url, {'inscricoes_ids': [self.inscricao_um.pk]})

        self.assertRedirects(resposta, self.url)
        presenca_um = Presenca.objects.get(inscricao=self.inscricao_um)
        presenca_dois = Presenca.objects.get(inscricao=self.inscricao_dois)
        self.assertTrue(presenca_um.confirmada)
        self.assertEqual(presenca_um.confirmada_por, self.gestor)
        self.assertIsNotNone(presenca_um.confirmada_em)
        self.assertFalse(presenca_dois.confirmada)

    def test_evento_nao_realizado_bloqueia_confirmacao(self):
        self.evento.status = 'PUBLICADO'
        self.evento.save(update_fields=['status'])

        resposta = self.client.post(self.url, {'inscricoes_ids': [self.inscricao_um.pk]})

        self.assertRedirects(resposta, self.url)
        self.assertFalse(Presenca.objects.filter(inscricao=self.inscricao_um).exists())

    def test_gestor_pode_corrigir_presenca_desmarcando_participante(self):
        self.client.post(self.url, {'inscricoes_ids': [self.inscricao_um.pk]})

        resposta = self.client.post(self.url, {})

        self.assertRedirects(resposta, self.url)
        presenca = Presenca.objects.get(inscricao=self.inscricao_um)
        self.assertFalse(presenca.confirmada)
        self.assertIsNone(presenca.confirmada_por)
        self.assertIsNone(presenca.confirmada_em)

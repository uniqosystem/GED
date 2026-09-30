from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from eventos.models import CampoInscricao, Evento, Inscricao


class EventosRegistrationTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('gestor', password='senha')
        self.evento = Evento.objects.create(
            titulo='Curso de Boas Praticas',
            slug='curso-boas-praticas',
            data_evento=date.today() + timedelta(days=3),
            hora_inicio=time(9, 0),
            hora_fim=time(12, 0),
            local='Auditorio CRF-PB',
            descricao='Curso para inscritos.',
            carga_horaria='3.00',
            limite_inscricoes=2,
            inscricoes_encerram_em=timezone.now() + timedelta(days=1),
            status='PUBLICADO',
            criado_por=self.usuario,
        )
        CampoInscricao.objects.create(
            evento=self.evento,
            nome='Instituição',
            chave='instituicao',
            obrigatorio=True,
        )
        self.url = reverse('eventos:inscricao', args=[self.evento.slug])
        self.dados = {
            'nome': 'Maria da Silva',
            'cpf': '529.982.247-25',
            'email': 'MARIA@EXEMPLO.COM',
            'telefone': '(83) 99999-9999',
            'consentiu_lgpd': 'on',
            'campo_instituicao': 'CRF-PB',
        }

    def test_inscricao_valida_normaliza_dados_e_respostas(self):
        resposta = self.client.post(self.url, self.dados)

        self.assertRedirects(
            resposta,
            reverse('eventos:inscricao_sucesso', args=[self.evento.slug]),
        )
        inscricao = Inscricao.objects.get()
        self.assertEqual(inscricao.cpf, '52998224725')
        self.assertEqual(inscricao.email, 'maria@exemplo.com')
        self.assertEqual(inscricao.respostas, {'campo_instituicao': 'CRF-PB'})

    def test_cpf_invalido_impede_inscricao(self):
        dados = {**self.dados, 'cpf': '111.111.111-11'}

        resposta = self.client.post(self.url, dados)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Informe um CPF válido.')
        self.assertFalse(Inscricao.objects.exists())

    def test_cpf_duplicado_impede_nova_inscricao(self):
        self.client.post(self.url, self.dados)

        resposta = self.client.post(self.url, self.dados)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Já existe uma inscrição ativa')
        self.assertEqual(Inscricao.objects.count(), 1)

    def test_limite_de_vagas_impede_nova_inscricao(self):
        Inscricao.objects.create(
            evento=self.evento,
            nome='Pessoa Um',
            cpf='39053344705',
            email='um@example.com',
            telefone='83999990000',
            consentiu_lgpd=True,
        )
        Inscricao.objects.create(
            evento=self.evento,
            nome='Pessoa Dois',
            cpf='12345678909',
            email='dois@example.com',
            telefone='83999990001',
            consentiu_lgpd=True,
        )

        resposta = self.client.post(self.url, {**self.dados, 'cpf': '52998224725'})

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'inscrições estão encerradas')
        self.assertEqual(Inscricao.objects.count(), 2)

    def test_prazo_encerrado_impede_inscricao(self):
        self.evento.inscricoes_encerram_em = timezone.now() - timedelta(minutes=1)
        self.evento.save(update_fields=['inscricoes_encerram_em'])

        resposta = self.client.get(self.url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'As inscrições estão encerradas')
        self.assertNotContains(resposta, 'Confirmar inscrição')

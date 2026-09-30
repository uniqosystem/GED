from datetime import date, time, timedelta
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import LogAuditoria, Setor
from eventos.models import CampoInscricao, Evento, Inscricao, caminho_imagem_evento


class EventosManagementTests(TestCase):
    def setUp(self):
        self.setor_eventos = Setor.objects.create(
            nome='Cursos e Eventos',
            caminho_rede='C:\\GED\\Cursos e Eventos',
        )
        self.outro_setor = Setor.objects.create(
            nome='Administrativo',
            caminho_rede='C:\\GED\\Administrativo',
        )
        self.gestor = self.criar_usuario('gestor', self.setor_eventos)
        self.outro_usuario = self.criar_usuario('administrativo', self.outro_setor)
        self.url = reverse('eventos:gestao_lista')

    def criar_usuario(self, username, setor):
        usuario = User.objects.create_user(username, password='senha')
        usuario.perfil.setor = setor
        usuario.perfil.password_changed = True
        usuario.perfil.save(update_fields=['setor', 'password_changed'])
        return usuario

    def test_usuario_nao_autenticado_nao_acessa_gestao(self):
        resposta = self.client.get(self.url)

        self.assertRedirects(resposta, f'{reverse("inicio")}?next={self.url}')

    def test_usuario_de_outro_setor_nao_acessa_gestao(self):
        self.client.force_login(self.outro_usuario)

        resposta = self.client.get(self.url)

        destino = f'{reverse("inicio")}?{urlencode({"next": self.url})}'
        self.assertRedirects(resposta, destino)

    def test_gestor_visualiza_painel(self):
        self.client.force_login(self.gestor)

        resposta = self.client.get(self.url)

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Gestão de Eventos')

    def test_gestor_lista_fecha_evento_publicado_sem_vagas(self):
        evento = Evento.objects.create(
            titulo='Evento lotado',
            slug='evento-lotado',
            data_evento=date.today() + timedelta(days=3),
            hora_inicio=time(9, 0),
            local='Auditorio',
            descricao='Descricao',
            carga_horaria='2.00',
            limite_inscricoes=1,
            inscricoes_encerram_em=timezone.now() + timedelta(days=1),
            status='PUBLICADO',
            criado_por=self.gestor,
        )
        Inscricao.objects.create(
            evento=evento,
            nome='Inscrito Lotado',
            cpf='52998224725',
            email='lotado@example.com',
            telefone='83999990000',
            consentiu_lgpd=True,
        )
        self.client.force_login(self.gestor)

        self.client.get(self.url)

        evento.refresh_from_db()
        self.assertEqual(evento.status, 'ENCERRADO')

    def test_gestor_visualiza_formulario_na_pagina_sem_modal(self):
        self.client.force_login(self.gestor)

        resposta = self.client.get(reverse('eventos:gestao_criar'))

        self.assertEqual(resposta.status_code, 200)
        self.assertNotContains(resposta, 'Abrir formulário')
        self.assertContains(resposta, 'Salvar evento')
        self.assertContains(resposta, 'Nome do Evento')

    def test_gestor_cria_evento_e_campo_adicional(self):
        self.client.force_login(self.gestor)
        data_evento = date.today() + timedelta(days=5)
        dados = {
            'titulo': 'Seminario de Atualizacao',
            'data_evento': data_evento.isoformat(),
            'hora_inicio': '09:00',
            'hora_fim': '12:00',
            'local': 'Auditorio CRF-PB',
            'palestrantes': 'Equipe tecnica',
            'descricao': 'Descricao completa do evento.',
            'regras': 'Publico interessado.',
            'carga_horaria': '3.00',
            'limite_inscricoes': '80',
            'inscricoes_encerram_em': f'{data_evento.isoformat()}T08:00',
            'status': 'RASCUNHO',
            'campos_adicionais-TOTAL_FORMS': '1',
            'campos_adicionais-INITIAL_FORMS': '0',
            'campos_adicionais-MIN_NUM_FORMS': '0',
            'campos_adicionais-MAX_NUM_FORMS': '1000',
            'campos_adicionais-0-nome': 'Instituicao',
            'campos_adicionais-0-chave': 'instituicao',
            'campos_adicionais-0-obrigatorio': 'on',
            'campos_adicionais-0-ativo': 'on',
        }

        resposta = self.client.post(reverse('eventos:gestao_criar'), dados)

        self.assertRedirects(resposta, self.url)
        evento = Evento.objects.get(titulo='Seminario de Atualizacao')
        self.assertEqual(evento.criado_por, self.gestor)
        self.assertEqual(evento.slug, 'seminario-de-atualizacao')
        self.assertEqual(evento.limite_inscricoes, 80)
        self.assertTrue(CampoInscricao.objects.filter(evento=evento, chave='instituicao').exists())
        self.assertEqual(
            caminho_imagem_evento(evento, 'cartaz.png'),
            f'eventos/{evento.pk}-seminario-de-atualizacao/imagens/cartaz.png',
        )
        self.assertTrue(LogAuditoria.objects.filter(
            usuario=self.gestor,
            acao='CRIAR_EVENTO',
            descricao__contains=evento.titulo,
        ).exists())

    def test_gestor_visualiza_inscritos_do_evento(self):
        evento = Evento.objects.create(
            titulo='Evento para inscritos',
            slug='evento-para-inscritos',
            data_evento=date.today() + timedelta(days=3),
            hora_inicio=time(9, 0),
            local='Auditorio',
            descricao='Descricao',
            carga_horaria='2.00',
            limite_inscricoes=10,
            inscricoes_encerram_em=timezone.now() + timedelta(days=1),
            criado_por=self.gestor,
        )
        self.client.force_login(self.gestor)

        resposta = self.client.get(reverse('eventos:gestao_inscricoes', args=[evento.pk]))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, evento.titulo)

    def test_gestor_filtra_inscritos_por_nome(self):
        evento = Evento.objects.create(
            titulo='Evento com filtro',
            slug='evento-com-filtro',
            data_evento=date.today() + timedelta(days=3),
            hora_inicio=time(9, 0),
            local='Auditorio',
            descricao='Descricao',
            carga_horaria='2.00',
            limite_inscricoes=10,
            inscricoes_encerram_em=timezone.now() + timedelta(days=1),
            criado_por=self.gestor,
        )
        Inscricao.objects.create(
            evento=evento,
            nome='Ana Filtro',
            cpf='52998224725',
            email='ana@example.com',
            telefone='83999990000',
            consentiu_lgpd=True,
        )
        Inscricao.objects.create(
            evento=evento,
            nome='Bruno Outro',
            cpf='39053344705',
            email='bruno@example.com',
            telefone='83999990001',
            consentiu_lgpd=True,
        )
        self.client.force_login(self.gestor)

        resposta = self.client.get(
            reverse('eventos:gestao_inscricoes', args=[evento.pk]),
            {'q': 'Ana'},
        )

        self.assertContains(resposta, 'Ana Filtro')
        self.assertNotContains(resposta, 'Bruno Outro')

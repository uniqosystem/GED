from django.contrib.auth.models import User
from django.test import TestCase

from core.models import LogAuditoria, Setor

from .models import Tramitacao
from .services import (
    assinar_tramitacao,
    assinar_tramitacao_com_senha,
    criar_tramitacoes,
    criar_tramitacoes_para_usuario,
    devolver_tramitacao,
    editar_tramitacao,
    editar_tramitacao_devolvida,
    excluir_tramitacao_devolvida,
    finalizar_tramitacao,
    listar_caixa_entrada,
    receber_tramitacao,
    responder_tramitacao,
    resolver_destinos_edicao,
    usuario_tem_acesso_tramitacao,
)


class TramitationWorkflowTests(TestCase):
    def setUp(self):
        self.setor_origem = Setor.objects.create(nome='Workflow Origem', caminho_rede='C:\\GED\\Workflow Origem')
        self.setor_destino = Setor.objects.create(nome='Workflow Destino', caminho_rede='C:\\GED\\Workflow Destino')
        self.remetente = User.objects.create_user('workflow_remetente', password='senha')
        self.destinatario = User.objects.create_user('workflow_destinatario', password='senha')
        self.remetente.perfil.setor = self.setor_origem
        self.remetente.perfil.save()
        self.destinatario.perfil.setor = self.setor_destino
        self.destinatario.perfil.save()

    def criar_tramitacao(self, aguardar=False, exige_assinatura=False):
        return Tramitacao.objects.create(
            protocolo=f'WORKFLOW-{Tramitacao.objects.count() + 1:04d}',
            criador=self.remetente,
            remetente=self.remetente,
            setor_origem=self.setor_origem,
            setor_destino=self.setor_destino,
            usuario_destino=self.destinatario,
            titulo='Workflow',
            despacho='Despacho inicial',
            status='PENDENTE',
            aguardar_resposta=aguardar,
            exige_assinatura=exige_assinatura,
        )

    def responder(self, tramitacao, usuario, despacho, aguardar=False):
        responder_tramitacao(
            tramitacao,
            usuario,
            {
                'despacho': despacho,
                'observacao': '',
                'aguardar_resposta': aguardar,
                'usuario_destino': '',
            },
            [],
        )

    def test_fluxo_normal_receber_e_concluir(self):
        tramitacao = self.criar_tramitacao()
        receber_tramitacao(tramitacao, self.destinatario)
        finalizar_tramitacao(tramitacao, self.destinatario)
        tramitacao.refresh_from_db()
        self.assertEqual(tramitacao.status, 'CONCLUIDO')

    def test_tramitacao_sem_resposta_nao_pode_ser_respondida(self):
        tramitacao = self.criar_tramitacao()
        receber_tramitacao(tramitacao, self.destinatario)
        with self.assertRaisesMessage(ValueError, 'não exige resposta'):
            responder_tramitacao(
                tramitacao,
                self.destinatario,
                {'despacho': 'Resposta indevida', 'aguardar_resposta': False},
                [],
            )

    def test_concluida_nao_aparece_em_enviados(self):
        tramitacao = self.criar_tramitacao()
        receber_tramitacao(tramitacao, self.destinatario)
        finalizar_tramitacao(tramitacao, self.destinatario)
        recebidos, enviados, arquivados, concluidos = listar_caixa_entrada(self.setor_origem, self.remetente)
        self.assertNotIn(tramitacao.id, enviados.values_list('id', flat=True))
        self.assertIn(tramitacao.id, concluidos.values_list('id', flat=True))

    def test_resposta_preserva_remetente_e_setor_originais(self):
        tramitacao = self.criar_tramitacao(aguardar=True)
        receber_tramitacao(tramitacao, self.destinatario)
        self.responder(tramitacao, self.destinatario, 'Resposta')
        tramitacao.refresh_from_db()
        self.assertEqual(tramitacao.remetente_original_id, self.remetente.id)
        self.assertEqual(tramitacao.setor_origem_original_id, self.setor_origem.id)

    def test_aguardando_resposta_conclui_apos_resposta_final(self):
        tramitacao = self.criar_tramitacao(aguardar=True)
        receber_tramitacao(tramitacao, self.destinatario)
        with self.assertRaises(ValueError):
            finalizar_tramitacao(tramitacao, self.destinatario)
        self.responder(tramitacao, self.destinatario, 'Resposta final')
        tramitacao.refresh_from_db()
        self.assertEqual(tramitacao.status, 'CONCLUIDO')

    def test_resposta_pode_aguardar_nova_resposta(self):
        tramitacao = self.criar_tramitacao(aguardar=True)
        receber_tramitacao(tramitacao, self.destinatario)
        self.responder(tramitacao, self.destinatario, 'Solicito retorno', True)
        tramitacao.refresh_from_db()
        self.assertEqual(tramitacao.status, 'PENDENTE')
        self.assertEqual(tramitacao.setor_destino, self.setor_origem)

    def test_multiplas_respostas_preservam_aguardar_por_etapa(self):
        tramitacao = self.criar_tramitacao(aguardar=True)
        receber_tramitacao(tramitacao, self.destinatario)
        self.responder(tramitacao, self.destinatario, 'Primeira resposta', True)
        receber_tramitacao(tramitacao, self.remetente)
        self.responder(tramitacao, self.remetente, 'Segunda resposta')
        historicos = list(tramitacao.historicos.order_by('id').values_list('aguardar_resposta', flat=True))
        self.assertEqual(historicos, [True, False])
        self.assertEqual(tramitacao.status, 'CONCLUIDO')

    def test_devolucao_retorna_acesso_ao_remetente(self):
        tramitacao = self.criar_tramitacao()
        devolver_tramitacao(tramitacao, self.destinatario)
        tramitacao.refresh_from_db()
        self.assertEqual(tramitacao.status, 'DEVOLVIDO')
        self.assertTrue(usuario_tem_acesso_tramitacao(self.remetente, tramitacao, 'editar'))

    def test_assinatura_e_obrigatoria_antes_de_concluir(self):
        tramitacao = self.criar_tramitacao(exige_assinatura=True)
        receber_tramitacao(tramitacao, self.destinatario)
        with self.assertRaises(ValueError):
            finalizar_tramitacao(tramitacao, self.destinatario)
        assinar_tramitacao(tramitacao, self.destinatario)
        finalizar_tramitacao(tramitacao, self.destinatario)
        tramitacao.refresh_from_db()
        self.assertTrue(tramitacao.assinado)
        self.assertEqual(tramitacao.status, 'CONCLUIDO')

    def test_servico_de_assinatura_valida_a_senha(self):
        tramitacao = self.criar_tramitacao(exige_assinatura=True)
        receber_tramitacao(tramitacao, self.destinatario)
        with self.assertRaisesMessage(ValueError, 'Senha incorreta'):
            assinar_tramitacao_com_senha(tramitacao, self.destinatario, 'senha-errada')
        tramitacao.refresh_from_db()
        self.assertFalse(tramitacao.assinado)
        assinar_tramitacao_com_senha(tramitacao, self.destinatario, 'senha')
        tramitacao.refresh_from_db()
        self.assertTrue(tramitacao.assinado)

    def test_servico_bloqueia_assinatura_duplicada(self):
        tramitacao = self.criar_tramitacao(exige_assinatura=True)
        receber_tramitacao(tramitacao, self.destinatario)
        assinar_tramitacao_com_senha(tramitacao, self.destinatario, 'senha')
        with self.assertRaisesMessage(ValueError, 'já foi assinado anteriormente'):
            assinar_tramitacao_com_senha(tramitacao, self.destinatario, 'senha')

    def test_assinatura_com_aguardar_resposta_permite_responder(self):
        tramitacao = self.criar_tramitacao(aguardar=True, exige_assinatura=True)
        receber_tramitacao(tramitacao, self.destinatario)
        assinar_tramitacao(tramitacao, self.destinatario)
        self.responder(tramitacao, self.destinatario, 'Resposta assinada')
        tramitacao.refresh_from_db()
        self.assertTrue(tramitacao.assinado)
        self.assertEqual(tramitacao.status, 'CONCLUIDO')

    def test_servico_cria_tramitacao_e_historico(self):
        criadas = criar_tramitacoes(
            {
                'tipo_documento': 'OFICIO',
                'titulo': 'Nova pelo serviço',
                'despacho': 'Despacho',
                'observacao': '',
                'aguardar_resposta': True,
                'exige_assinatura': False,
                'data_limite_resposta': None,
            },
            self.remetente,
            self.setor_origem,
            [self.setor_destino],
            [self.destinatario],
            [],
        )
        self.assertEqual(len(criadas), 1)
        self.assertEqual(criadas[0].historicos.count(), 1)
        self.assertEqual(criadas[0].setor_criador, self.setor_origem)

    def test_servico_cria_tramitacao_resolvendo_destinos(self):
        criadas = criar_tramitacoes_para_usuario(
            {
                'tipo_documento': 'OFICIO',
                'titulo': 'Destino resolvido pelo serviço',
                'despacho': 'Despacho',
                'observacao': '',
                'aguardar_resposta': False,
                'exige_assinatura': False,
                'data_limite_resposta': None,
                'setor_destino': [str(self.setor_destino.id)],
                'usuario_destino': [str(self.destinatario.id)],
            },
            self.remetente,
            [],
        )
        self.assertEqual(len(criadas), 1)
        self.assertEqual(criadas[0].setor_origem, self.setor_origem)
        self.assertEqual(criadas[0].setor_destino, self.setor_destino)
        self.assertEqual(criadas[0].usuario_destino, self.destinatario)

    def test_envio_rejeita_usuario_de_setor_incorreto(self):
        with self.assertRaisesMessage(ValueError, 'não pertence a um setor de destino'):
            criar_tramitacoes_para_usuario(
                {
                    'tipo_documento': 'OFICIO',
                    'titulo': 'Destino inválido',
                    'despacho': 'Despacho',
                    'observacao': '',
                    'aguardar_resposta': False,
                    'exige_assinatura': False,
                    'data_limite_resposta': None,
                    'setor_destino': [str(self.setor_origem.id)],
                    'usuario_destino': [str(self.destinatario.id)],
                },
                self.remetente,
                [],
            )

    def test_servico_edita_e_reenvia_tramitacao(self):
        tramitacao = self.criar_tramitacao()
        tramitacao.status = 'DEVOLVIDO'
        tramitacao.save(update_fields=['status'])
        editar_tramitacao(
            tramitacao,
            {
                'tipo_documento': 'MEMORANDO',
                'titulo': 'Editada',
                'despacho': 'Despacho corrigido',
                'observacao': 'Observação',
                'aguardar_resposta': False,
                'exige_assinatura': False,
                'data_limite_resposta': None,
            },
            self.setor_destino,
            self.destinatario,
        )
        tramitacao.refresh_from_db()
        self.assertEqual(tramitacao.status, 'PENDENTE')
        self.assertEqual(tramitacao.titulo, 'Editada')

    def test_servico_edita_devolvida_preserva_exigencia_de_assinatura(self):
        tramitacao = self.criar_tramitacao(aguardar=True, exige_assinatura=True)
        tramitacao.status = 'DEVOLVIDO'
        tramitacao.save(update_fields=['status'])
        editar_tramitacao_devolvida(
            tramitacao,
            self.remetente,
            {
                'tipo_documento': 'MEMORANDO',
                'titulo': 'Reenvio assinado',
                'despacho': 'Despacho corrigido',
                'observacao': '',
                'aguardar_resposta': True,
                'exige_assinatura': True,
                'data_limite_resposta': None,
            },
            self.setor_destino,
            self.destinatario,
        )
        tramitacao.refresh_from_db()
        self.assertTrue(tramitacao.aguardar_resposta)
        self.assertTrue(tramitacao.exige_assinatura)
        self.assertFalse(tramitacao.assinado)

    def test_servico_edita_devolvida_com_auditoria(self):
        tramitacao = self.criar_tramitacao()
        with self.assertRaisesMessage(ValueError, 'não pode ser editada'):
            editar_tramitacao_devolvida(
                tramitacao,
                self.remetente,
                {
                    'tipo_documento': 'MEMORANDO',
                    'titulo': 'Não deve editar',
                    'despacho': 'Sem edição',
                    'observacao': '',
                    'aguardar_resposta': False,
                    'exige_assinatura': False,
                    'data_limite_resposta': None,
                },
                self.setor_destino,
                self.destinatario,
            )
        tramitacao.status = 'DEVOLVIDO'
        tramitacao.save(update_fields=['status'])
        editar_tramitacao_devolvida(
            tramitacao,
            self.remetente,
            {
                'tipo_documento': 'MEMORANDO',
                'titulo': 'Editada por serviço',
                'despacho': 'Despacho corrigido',
                'observacao': 'Observação',
                'aguardar_resposta': False,
                'exige_assinatura': False,
                'data_limite_resposta': None,
            },
            self.setor_destino,
            self.destinatario,
        )
        tramitacao.refresh_from_db()
        self.assertEqual(tramitacao.status, 'PENDENTE')
        self.assertEqual(tramitacao.titulo, 'Editada por serviço')
        self.assertTrue(LogAuditoria.objects.filter(acao='EDITAR_TRAMITACAO', descricao__contains=tramitacao.protocolo).exists())

    def test_servico_exclui_apenas_tramitacao_devolvida(self):
        tramitacao = self.criar_tramitacao()
        with self.assertRaisesMessage(ValueError, 'não pode ser excluída'):
            excluir_tramitacao_devolvida(tramitacao, self.remetente)
        self.assertTrue(Tramitacao.objects.filter(pk=tramitacao.pk).exists())
        tramitacao.status = 'DEVOLVIDO'
        tramitacao.save(update_fields=['status'])
        protocolo = tramitacao.protocolo
        excluir_tramitacao_devolvida(tramitacao, self.remetente)
        self.assertFalse(Tramitacao.objects.filter(protocolo=protocolo).exists())
        self.assertTrue(LogAuditoria.objects.filter(acao='EXCLUIR_TRAMITACAO', descricao__contains=protocolo).exists())

    def test_servico_resolve_destinos_da_edicao(self):
        setor, usuario = resolver_destinos_edicao(
            {
                'setor_destino': [str(self.setor_destino.id)],
                'usuario_destino': [str(self.destinatario.id)],
            },
            self.setor_origem,
        )
        self.assertEqual(setor, self.setor_destino)
        self.assertEqual(usuario, self.destinatario)
        with self.assertRaisesMessage(ValueError, 'apenas um setor'):
            resolver_destinos_edicao(
                {
                    'setor_destino': [str(self.setor_origem.id), str(self.setor_destino.id)],
                    'usuario_destino': [],
                },
                self.setor_origem,
            )
        with self.assertRaisesMessage(ValueError, 'não pertence ao setor'):
            resolver_destinos_edicao(
                {
                    'setor_destino': [str(self.setor_origem.id)],
                    'usuario_destino': [str(self.destinatario.id)],
                },
                self.setor_origem,
            )

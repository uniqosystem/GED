from django.contrib.auth.models import User
from django.core import management
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.utils.datastructures import MultiValueDict

from core.models import LogAuditoria, Setor

from .models import AnexoTramitacao, HistoricoTramitacao, Tramitacao
from .services import (
	contar_notificacoes_pendentes,
	listar_anexos_tramitacao,
	listar_caixa_entrada,
	listar_usuarios_por_setores,
	montar_historico_tramitacao,
	obter_tramitacao_autorizada,
	resolver_arquivos_upload,
	usuario_tem_acesso_tramitacao,
)


class TramitacaoSecurityTests(TestCase):
	def setUp(self):
		self.setor_origem = Setor.objects.create(nome='Origem', caminho_rede='C:\\GED\\Origem')
		self.setor_destino = Setor.objects.create(nome='Destino', caminho_rede='C:\\GED\\Destino')
		self.remetente = User.objects.create_user('remetente', password='senha')
		self.destinatario = User.objects.create_user('destinatario', password='senha')
		self.remetente.perfil.setor = self.setor_origem
		self.remetente.perfil.save()
		self.destinatario.perfil.setor = self.setor_destino
		self.destinatario.perfil.save()
		self.tramitacao = Tramitacao.objects.create(
			protocolo='TEST-0001',
			criador=self.remetente,
			remetente=self.remetente,
			setor_origem=self.setor_origem,
			setor_destino=self.setor_destino,
			titulo='Teste',
			despacho='Despacho',
			status='PENDENTE',
		)

	def test_apenas_destinatario_recebe(self):
		self.assertTrue(usuario_tem_acesso_tramitacao(self.destinatario, self.tramitacao, 'receber'))
		self.assertFalse(usuario_tem_acesso_tramitacao(self.remetente, self.tramitacao, 'receber'))

	def test_servico_obtem_tramitacao_autorizada(self):
		carregada = obter_tramitacao_autorizada(self.destinatario, self.tramitacao.id, 'receber')
		self.assertEqual(carregada.id, self.tramitacao.id)

	def test_servico_obter_tramitacao_sem_permissao_levanta_erro(self):
		with self.assertRaises(PermissionDenied):
			obter_tramitacao_autorizada(self.remetente, self.tramitacao.id, 'receber')

	def test_servico_obter_tramitacao_inexistente_levanta_doesnotexist(self):
		with self.assertRaises(Tramitacao.DoesNotExist):
			obter_tramitacao_autorizada(self.destinatario, 999999, 'visualizar')

	def test_protocolo_e_unico(self):
		with self.assertRaises(IntegrityError):
			with transaction.atomic():
				Tramitacao.objects.create(
					protocolo='TEST-0001', criador=self.remetente, remetente=self.remetente,
					setor_origem=self.setor_origem, setor_destino=self.setor_destino,
					titulo='Duplicado', despacho='Despacho',
				)

	def test_contagem_notificacoes_pendentes(self):
		self.assertEqual(contar_notificacoes_pendentes(self.destinatario), 1)

	def test_contagem_notificacoes_sem_setor_retorna_zero(self):
		usuario_sem_setor = User.objects.create_user('sem_setor', password='senha')
		usuario_sem_setor.perfil.setor = None
		usuario_sem_setor.perfil.save()
		self.assertEqual(contar_notificacoes_pendentes(usuario_sem_setor), 0)

	def test_servico_monta_historico_com_anexos(self):
		historico = HistoricoTramitacao.objects.create(
			tramitacao=self.tramitacao, remetente=self.remetente,
			setor_origem=self.setor_origem, despacho='Despacho historico',
		)
		AnexoTramitacao.objects.create(
			tramitacao=self.tramitacao, historico=historico,
			arquivo='tramitacoes/2026/TESTE/anexo_historico.txt',
		)
		data = montar_historico_tramitacao(self.tramitacao)
		self.assertEqual(len(data), 1)
		self.assertEqual(data[0]['despacho'], 'Despacho historico')
		self.assertEqual(data[0]['remetente'], self.remetente.username)
		self.assertEqual(data[0]['anexos'][0]['nome'], 'anexo_historico.txt')

	def test_servico_lista_usuarios_por_setor(self):
		usuarios = listar_usuarios_por_setores([str(self.setor_destino.id)])
		self.assertTrue(any(u['id'] == self.destinatario.id for u in usuarios))
		registro = next(u for u in usuarios if u['id'] == self.destinatario.id)
		self.assertEqual(registro['setor'], self.setor_destino.nome)

	def test_servico_lista_usuarios_sem_setor_retorna_vazio(self):
		self.assertEqual(listar_usuarios_por_setores([]), [])

	def test_servico_lista_caixa_entrada_respeita_status_e_destinatario(self):
		for protocolo, status in (
			('TEST-CAIXA-ENVIADO', 'PENDENTE'),
			('TEST-CAIXA-ARQ', 'ARQUIVADO'),
			('TEST-CAIXA-CONC', 'CONCLUIDO'),
		):
			Tramitacao.objects.create(
				protocolo=protocolo, criador=self.remetente, remetente=self.remetente,
				setor_origem=self.setor_origem, setor_destino=self.setor_destino,
				titulo=status, despacho='Despacho', status=status,
			)
		recebidos, enviados, arquivados, concluidos = listar_caixa_entrada(self.setor_destino, self.destinatario)
		self.assertEqual(recebidos.count(), 2)
		self.assertEqual(enviados.count(), 0)
		self.assertEqual(arquivados.count(), 1)
		self.assertEqual(concluidos.count(), 1)

	def test_servico_lista_anexos_da_tramitacao(self):
		AnexoTramitacao.objects.create(tramitacao=self.tramitacao, arquivo='tramitacoes/2026/TESTE/arquivo\\anexo1.pdf')
		AnexoTramitacao.objects.create(tramitacao=self.tramitacao, arquivo='tramitacoes/2026/TESTE/anexo2.pdf')
		anexos = listar_anexos_tramitacao(self.tramitacao)
		self.assertEqual(len(anexos), 2)
		self.assertEqual({a['nome'] for a in anexos}, {'anexo1.pdf', 'anexo2.pdf'})

	def test_servico_resolve_arquivos_upload_com_fallback(self):
		arquivo = SimpleUploadedFile('arquivo.txt', b'dados')
		resultado = resolver_arquivos_upload(MultiValueDict({'arquivo_anexo': [arquivo]}), ['anexos', 'arquivo_anexo', 'arquivo'])
		self.assertEqual(len(resultado), 1)
		self.assertEqual(resultado[0].name, 'arquivo.txt')

	def test_servico_resolve_arquivos_upload_sem_campos_retorna_lista_vazia(self):
		self.assertEqual(resolver_arquivos_upload(MultiValueDict(), ['anexos', 'arquivo_anexo', 'arquivo']), [])

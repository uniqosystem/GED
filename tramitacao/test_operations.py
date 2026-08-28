from datetime import timedelta
import os
import tempfile

from django.contrib.auth.models import User
from django.core import management
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import LogAuditoria, Setor

from .models import AnexoTramitacao, Tramitacao


class VencimentoCommandTests(TestCase):
	def setUp(self):
		self.setor_origem = Setor.objects.create(nome='Origem', caminho_rede='C:\\GED\\Origem')
		self.setor_destino = Setor.objects.create(nome='Destino', caminho_rede='C:\\GED\\Destino')
		self.remetente = User.objects.create_user('remetente_vencido', password='senha')
		self.destinatario = User.objects.create_user('destinatario_vencido', password='senha')
		self.remetente.perfil.setor = self.setor_origem
		self.remetente.perfil.save()
		self.destinatario.perfil.setor = self.setor_destino
		self.destinatario.perfil.save()
		self.tramitacao = Tramitacao.objects.create(
			protocolo='TEST-0002', criador=self.remetente, remetente=self.remetente,
			setor_origem=self.setor_origem, setor_destino=self.setor_destino,
			usuario_destino=self.destinatario, titulo='Vencida', despacho='Despacho',
			status='PENDENTE', aguardar_resposta=True,
			data_limite_resposta=timezone.now().date() - timedelta(days=1),
		)

	def test_comando_devolve_tramitacao_vencida(self):
		management.call_command('processar_tramitacoes_vencidas')
		self.tramitacao.refresh_from_db()
		self.assertEqual(self.tramitacao.status, 'RECEBIDO')
		self.assertTrue(self.tramitacao.auto_devolvido)
		self.assertEqual(self.tramitacao.historicos.count(), 1)
		self.assertEqual(self.tramitacao.usuario_destino, self.remetente)
		self.assertTrue(self.tramitacao.historicos.first().aguardar_resposta)
		self.assertTrue(LogAuditoria.objects.filter(acao='DEVOLVER_TRAMITACAO').exists())


@override_settings(MEDIA_ROOT='C:\\TESTE\\TRAMITACAO_TESTE')
class TramitationAttachmentCleanupTests(TestCase):
	def setUp(self):
		self.temp_dir = tempfile.TemporaryDirectory(dir=r'C:\TESTE')
		self.override = override_settings(MEDIA_ROOT=self.temp_dir.name)
		self.override.enable()
		self.setor = Setor.objects.create(nome='Anexo Setor', caminho_rede='C:\\GED\\Anexo')
		self.usuario = User.objects.create_user('anexo_usuario', password='senha')
		self.usuario.perfil.setor = self.setor
		self.usuario.perfil.save()

	def tearDown(self):
		self.override.disable()
		self.temp_dir.cleanup()

	def test_exclusao_da_tramitacao_remove_arquivo_fisico(self):
		tramitacao = Tramitacao.objects.create(
			protocolo='ANEXO-0001', criador=self.usuario, remetente=self.usuario,
			setor_origem=self.setor, setor_destino=self.setor,
			titulo='Anexo', despacho='Teste',
		)
		anexo = AnexoTramitacao.objects.create(
			tramitacao=tramitacao, arquivo=SimpleUploadedFile('documento.txt', b'conteudo'),
		)
		caminho = anexo.arquivo.path
		self.assertTrue(os.path.exists(caminho))
		tramitacao.delete()
		self.assertFalse(os.path.exists(caminho))

	def test_comando_lista_e_remove_apenas_arquivos_orfaos(self):
		root = os.path.join(self.temp_dir.name, 'tramitacoes', '2026', 'TESTE')
		os.makedirs(root, exist_ok=True)
		referenciado = os.path.join(root, 'referenciado.txt')
		orfao = os.path.join(root, 'orfao.txt')
		with open(referenciado, 'wb') as arquivo:
			arquivo.write(b'referenciado')
		with open(orfao, 'wb') as arquivo:
			arquivo.write(b'orfao')
		tramitacao = Tramitacao.objects.create(
			protocolo='ANEXO-0002', criador=self.usuario, remetente=self.usuario,
			setor_origem=self.setor, setor_destino=self.setor,
			titulo='Anexo referenciado', despacho='Teste',
		)
		AnexoTramitacao.objects.create(tramitacao=tramitacao, arquivo='tramitacoes/2026/TESTE/referenciado.txt')
		management.call_command('limpar_anexos_orfaos')
		self.assertTrue(os.path.exists(orfao))
		self.assertTrue(os.path.exists(referenciado))
		management.call_command('limpar_anexos_orfaos', apply=True)
		self.assertFalse(os.path.exists(orfao))
		self.assertTrue(os.path.exists(referenciado))

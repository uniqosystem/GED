import os
import shutil
import tempfile
import urllib.parse

from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from core.models import LogAuditoria, RegistroLixeira
from core.file_delivery import abrir_arquivo_autorizado, tipo_conteudo_arquivo
from core.navigation_services import construir_breadcrumbs, obter_configuracao_modulo, por_pagina_seguro
from core.rename_service import renomear_item
from core.storage_services import criar_subpasta_ged, upload_multiplo_permitido
from core.trash_queries import listar_itens_lixeira
from core.trash_services import esvaziar_lixeira, excluir_itens_lixeira


@override_settings(
	GED_BASE_DIR='C:\\TESTE\\FILESYSTEM_GED',
	SETORES_BASE_DIR='C:\\TESTE\\FILESYSTEM_SETORES',
	TRAMITACAO_DIR='C:\\TESTE\\FILESYSTEM_TRAMITACAO',
	LIXEIRA_DIR='C:\\TESTE\\FILESYSTEM_LIXEIRA',
)
class FileSystemOperationTests(TestCase):
	def setUp(self):
		self.usuario = User.objects.create_superuser('admin_filesystem', password='senha')
		for caminho in (
			settings.GED_BASE_DIR,
			settings.SETORES_BASE_DIR,
			settings.TRAMITACAO_DIR,
			settings.LIXEIRA_DIR,
		):
			os.makedirs(caminho, exist_ok=True)
		self.pasta = tempfile.mkdtemp(dir=settings.GED_BASE_DIR)

	def tearDown(self):
		for caminho in (settings.GED_BASE_DIR, settings.SETORES_BASE_DIR, settings.TRAMITACAO_DIR, settings.LIXEIRA_DIR):
			shutil.rmtree(caminho, ignore_errors=True)

	def test_renomeia_arquivo_preservando_extensao(self):
		caminho = os.path.join(self.pasta, 'original.pdf')
		with open(caminho, 'wb') as arquivo:
			arquivo.write(b'%PDF-1.7')

		renomeado, conflito = renomear_item(self.usuario, caminho, 'novo nome')

		self.assertTrue(renomeado)
		self.assertFalse(conflito)
		self.assertTrue(os.path.exists(os.path.join(self.pasta, 'novo nome.pdf')))

	def test_abre_arquivo_autorizado_e_informa_mime(self):
		caminho = os.path.join(self.pasta, 'imagem.png')
		with open(caminho, 'wb') as arquivo:
			arquivo.write(b'\x89PNG\r\n\x1a\n')

		arquivo, caminho_seguro = abrir_arquivo_autorizado(self.usuario, caminho)

		try:
			self.assertEqual(caminho_seguro, os.path.realpath(caminho))
			self.assertEqual(tipo_conteudo_arquivo(caminho_seguro), 'image/png')
			self.assertEqual(arquivo.read(), b'\x89PNG\r\n\x1a\n')
		finally:
			arquivo.close()

	def test_nao_abre_arquivo_fora_das_raizes_autorizadas(self):
		pasta_externa = tempfile.mkdtemp()
		caminho = os.path.join(pasta_externa, 'externo.txt')
		open(caminho, 'wb').close()

		try:
			with self.assertRaises(PermissionDenied):
				abrir_arquivo_autorizado(self.usuario, caminho)
		finally:
			shutil.rmtree(pasta_externa, ignore_errors=True)

	def test_renomeacao_rejeita_nome_com_caractere_reservado(self):
		caminho = os.path.join(self.pasta, 'original.txt')
		open(caminho, 'wb').close()

		with self.assertRaises(ValidationError):
			renomear_item(self.usuario, caminho, 'novo:nome')

	def test_usuario_sem_acesso_nao_renomeia_item(self):
		usuario = User.objects.create_user('usuario_filesystem', password='senha')
		caminho = os.path.join(self.pasta, 'original.txt')
		open(caminho, 'wb').close()

		with self.assertRaises(PermissionDenied):
			renomear_item(usuario, caminho, 'novo')

	def test_apagar_e_restaurar_preserva_registro_original(self):
		self.usuario.perfil.password_changed = True
		self.usuario.perfil.save(update_fields=['password_changed'])
		caminho = os.path.join(self.pasta, 'original.txt')
		open(caminho, 'wb').close()
		self.client.force_login(self.usuario)

		resposta = self.client.post('/apagar/', {'caminho_atual': caminho, 'crf': 'bypass'})

		self.assertEqual(resposta.status_code, 302)
		registro = RegistroLixeira.objects.get(caminho_original=caminho)
		caminho_lixeira = os.path.join(settings.LIXEIRA_DIR, registro.nome_na_lixeira)
		self.assertFalse(os.path.exists(caminho))
		self.assertTrue(os.path.exists(caminho_lixeira))

		resposta = self.client.post('/lixeira/restaurar/', {'caminho_lixeira': caminho_lixeira})

		self.assertEqual(resposta.status_code, 302)
		self.assertTrue(os.path.exists(caminho))
		self.assertFalse(RegistroLixeira.objects.filter(pk=registro.pk).exists())

	def test_exclusao_multipla_move_itens_e_contabiliza_sucessos(self):
		caminhos = [os.path.join(self.pasta, f'arquivo_{indice}.txt') for indice in (1, 2)]
		for caminho in caminhos:
			open(caminho, 'wb').close()

		sucessos, erros = excluir_itens_lixeira(self.usuario, caminhos)

		self.assertEqual((sucessos, erros), (2, 0))
		self.assertEqual(RegistroLixeira.objects.filter(apagado_por=self.usuario).count(), 2)
		self.assertEqual(LogAuditoria.objects.filter(acao='EXCLUSAO_MUTIPLA').count(), 2)

	def test_esvaziamento_remove_arquivos_e_registra_auditoria(self):
		os.makedirs(settings.LIXEIRA_DIR, exist_ok=True)
		caminho = os.path.join(settings.LIXEIRA_DIR, 'permanente.txt')
		with open(caminho, 'wb') as arquivo:
			arquivo.write(b'dados')

		contador = esvaziar_lixeira(self.usuario)

		self.assertEqual(contador, 1)
		self.assertFalse(os.path.exists(caminho))
		self.assertTrue(LogAuditoria.objects.filter(acao='APAGAR').exists())

	def test_listagem_aplica_filtros_e_associa_metadados(self):
		os.makedirs(settings.LIXEIRA_DIR, exist_ok=True)
		caminho = os.path.join(settings.LIXEIRA_DIR, 'documento.txt')
		with open(caminho, 'wb') as arquivo:
			arquivo.write(b'dados')
		RegistroLixeira.objects.create(
			nome_na_lixeira='documento.txt',
			caminho_original=os.path.join(self.pasta, 'documento.txt'),
			apagado_por=self.usuario,
		)

		arquivos = listar_itens_lixeira('documento', 'Arquivo')

		self.assertEqual(len(arquivos), 1)
		self.assertEqual(arquivos[0]['nome'], 'documento.txt')
		self.assertEqual(arquivos[0]['apagado_por'], self.usuario.username)
		self.assertEqual(arquivos[0]['tamanho'], '0.0 KB')

	def test_cria_subpasta_com_nome_valido(self):
		criada, nome = criar_subpasta_ged(self.usuario, self.pasta, 'Processos 2026')

		self.assertTrue(criada)
		self.assertEqual(nome, 'Processos 2026')
		self.assertTrue(os.path.isdir(os.path.join(self.pasta, nome)))

	def test_rejeita_subpasta_com_nome_reservado(self):
		with self.assertRaises(ValidationError):
			criar_subpasta_ged(self.usuario, self.pasta, 'CON')

	def test_navegacao_nao_confunde_prefixo_de_diretorio(self):
		raiz_pf = os.path.join(settings.GED_BASE_DIR, 'PESSOA FISICA')
		caminho_parecido = os.path.join(settings.GED_BASE_DIR, 'PESSOA FISICA_EXTRA')
		os.makedirs(caminho_parecido, exist_ok=True)
		os.makedirs(raiz_pf, exist_ok=True)
		cliente = Client()
		self.usuario.perfil.password_changed = True
		self.usuario.perfil.save(update_fields=['password_changed'])
		cliente.force_login(self.usuario)

		resposta = cliente.get(
			f'/navegar/pessoa-fisica/?pasta={urllib.parse.quote(caminho_parecido)}'
		)

		self.assertEqual(resposta.status_code, 200)
		self.assertEqual(resposta.context['caminho_pasta_atual'], os.path.realpath(raiz_pf))

	def test_configuracao_resolve_raiz_de_cada_modulo(self):
		self.assertEqual(
			obter_configuracao_modulo('pessoa-fisica')['raiz'],
			os.path.join(settings.GED_BASE_DIR, 'PESSOA FISICA'),
		)
		self.assertEqual(
			obter_configuracao_modulo('setores')['raiz'],
			settings.SETORES_BASE_DIR,
		)
		self.assertIsNone(obter_configuracao_modulo('invalido'))

	def test_breadcrumbs_montam_caminhos_da_subpasta(self):
		raiz = os.path.join(settings.GED_BASE_DIR, 'PESSOA FISICA')
		caminho = os.path.join(raiz, '2026', 'marco')

		partes, pasta_pai = construir_breadcrumbs(raiz, caminho)

		self.assertEqual([parte['nome'] for parte in partes], ['2026', 'marco'])
		self.assertEqual(partes[-1]['caminho'], caminho)
		self.assertEqual(pasta_pai, os.path.join(raiz, '2026'))

	def test_paginacao_segura_fica_no_servico_de_navegacao(self):
		self.assertEqual(por_pagina_seguro('abc', 25), 25)
		self.assertEqual(por_pagina_seguro('0', 25), 1)
		self.assertEqual(por_pagina_seguro('10', 25), 10)

	def test_upload_multiplo_salva_arquivo_e_retorna_json(self):
		self.usuario.perfil.password_changed = True
		self.usuario.perfil.save(update_fields=['password_changed'])
		cliente = Client()
		cliente.force_login(self.usuario)
		arquivo = SimpleUploadedFile('anexo.txt', b'conteudo', content_type='text/plain')

		resposta = cliente.post(
			'/upload-multiplo-ajax/',
			{'caminho_atual': self.pasta, 'file': arquivo},
		)

		self.assertEqual(resposta.status_code, 200)
		self.assertEqual(resposta.json(), {'message': 'Sucesso!', 'nome': 'anexo.txt'})
		self.assertTrue(os.path.exists(os.path.join(self.pasta, 'anexo.txt')))

	def test_upload_multiplo_bloqueia_raizes_e_permite_subpastas(self):
		raiz_pf = os.path.join(settings.GED_BASE_DIR, 'PESSOA FISICA')
		raiz_parecida = os.path.join(settings.GED_BASE_DIR, 'PESSOA FISICA_EXTRA')

		self.assertFalse(upload_multiplo_permitido(raiz_pf))
		self.assertTrue(upload_multiplo_permitido(os.path.join(raiz_pf, '2026')))
		self.assertTrue(upload_multiplo_permitido(raiz_parecida))
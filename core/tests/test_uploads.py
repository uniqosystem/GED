import os
import tempfile
import urllib.parse

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from core.file_services import salvar_upload_ged, validar_caminho_seguro, validar_nome_seguro
from core.models import LogAuditoria


@override_settings(
	GED_BASE_DIR='C:\\TESTE\\GED_TESTE',
	SETORES_BASE_DIR='C:\\TESTE\\SETORES_TESTE',
	TRAMITACAO_DIR='C:\\TESTE\\TRAMITACAO_TESTE',
)
class GedUploadTests(TestCase):
	def setUp(self):
		os.makedirs(settings.GED_BASE_DIR, exist_ok=True)
		self.temp_dir = tempfile.TemporaryDirectory(dir=settings.GED_BASE_DIR)
		self.usuario = User.objects.create_superuser('admin_upload', password='senha')

	def tearDown(self):
		self.temp_dir.cleanup()

	def test_upload_grava_e_impede_sobrescrita(self):
		arquivo = SimpleUploadedFile('documento.txt', b'conteudo')
		nome, caminho = salvar_upload_ged(self.usuario, arquivo, self.temp_dir.name)

		self.assertEqual(nome, 'documento.txt')
		self.assertTrue(os.path.exists(caminho))
		self.assertEqual(LogAuditoria.objects.filter(acao='UPLOAD').count(), 1)

		with self.assertRaises(ValidationError):
			salvar_upload_ged(self.usuario, SimpleUploadedFile('documento.txt', b'novo conteudo'), self.temp_dir.name)

	def test_visualizacao_usa_mime_do_arquivo(self):
		administrador = User.objects.create_superuser('admin_visualizacao', password='senha')
		administrador.perfil.password_changed = True
		administrador.perfil.save(update_fields=['password_changed'])
		pdf_path = os.path.join(self.temp_dir.name, 'documento.pdf')
		png_path = os.path.join(self.temp_dir.name, 'imagem.png')
		with open(pdf_path, 'wb') as arquivo_pdf:
			arquivo_pdf.write(b'%PDF-1.7\n')
		with open(png_path, 'wb') as arquivo_png:
			arquivo_png.write(b'\x89PNG\r\n\x1a\n')

		self.client.force_login(administrador)
		response_pdf = self.client.get(f'/visualizar/?caminho={urllib.parse.quote(pdf_path)}')
		response_png = self.client.get(f'/visualizar/?caminho={urllib.parse.quote(png_path)}')

		self.assertEqual(response_pdf['Content-Type'], 'application/pdf')
		self.assertEqual(response_png['Content-Type'], 'image/png')
		self.assertEqual(response_pdf['X-Frame-Options'], 'SAMEORIGIN')
		self.assertEqual(response_png['X-Frame-Options'], 'SAMEORIGIN')
		response_pdf.close()
		response_png.close()

	def test_caminho_com_link_para_fora_da_raiz_e_rejeitado(self):
		pasta_externa = tempfile.TemporaryDirectory()
		pasta_link = os.path.join(self.temp_dir.name, 'atalho')
		try:
			os.symlink(pasta_externa.name, pasta_link, target_is_directory=True)
		except (OSError, NotImplementedError):
			pasta_externa.cleanup()
			self.skipTest('O sistema não permite criar links simbólicos neste ambiente.')

		try:
			with self.assertRaises(PermissionDenied):
				validar_caminho_seguro(os.path.join(pasta_link, 'arquivo.txt'))
		finally:
			pasta_externa.cleanup()


@override_settings(UPLOAD_MAX_SIZE=1024, UPLOAD_ALLOWED_EXTENSIONS=['.txt', '.pdf', '.docx', '.png'])
class UploadValidationTests(TestCase):
	def test_rejeita_arquivo_acima_do_limite(self):
		from core.file_validation import validar_upload
		with self.assertRaisesMessage(ValidationError, 'excede o limite'):
			validar_upload(SimpleUploadedFile('grande.txt', b'1' * 2048, content_type='text/plain'))

	def test_rejeita_extensao_nao_permitida(self):
		from core.file_validation import validar_upload
		with self.assertRaisesMessage(ValidationError, 'extensão do arquivo não é permitida'):
			validar_upload(SimpleUploadedFile('script.exe', b'123', content_type='application/octet-stream'))

	def test_rejeita_caracteres_invalidos_de_nome_no_windows(self):
		with self.assertRaisesMessage(ValidationError, 'caracteres inválidos'):
			validar_nome_seguro('documento:alternativo.txt', eh_arquivo=True)

	def test_rejeita_nome_terminado_em_ponto_ou_espaco(self):
		with self.assertRaisesMessage(ValidationError, 'terminar com espaço ou ponto'):
			validar_nome_seguro('documento. ')

	def test_aceita_nome_comum_com_acentos_e_espacos(self):
		self.assertIsNone(validar_nome_seguro('Ofício de João - versão 2.pdf', eh_arquivo=True))

	def test_rejeita_mime_incompativel(self):
		from core.file_validation import validar_upload
		with self.assertRaisesMessage(ValidationError, 'tipo MIME'):
			validar_upload(SimpleUploadedFile('arquivo.txt', b'123', content_type='application/pdf'))

	def test_aceita_arquivo_valido(self):
		from core.file_validation import validar_upload
		arquivo = SimpleUploadedFile('arquivo.txt', b'123', content_type='text/plain')
		self.assertIs(validar_upload(arquivo), arquivo)

	def test_rejeita_pdf_com_conteudo_invalido(self):
		from core.file_validation import validar_upload
		with self.assertRaisesMessage(ValidationError, 'PDF válido'):
			validar_upload(SimpleUploadedFile('arquivo.pdf', b'nao e pdf', content_type='application/pdf'))

	def test_aceita_pdf_com_assinatura_valida(self):
		from core.file_validation import validar_upload
		arquivo = SimpleUploadedFile('arquivo.pdf', b'%PDF-1.7\nconteudo', content_type='application/pdf')
		self.assertIs(validar_upload(arquivo), arquivo)

	def test_rejeita_imagem_png_com_conteudo_invalido(self):
		from core.file_validation import validar_upload
		with self.assertRaisesMessage(ValidationError, 'imagem PNG válida'):
			validar_upload(SimpleUploadedFile('imagem.png', b'nao e png', content_type='image/png'))

	def test_aceita_imagem_png_com_assinatura_valida(self):
		from core.file_validation import validar_upload
		arquivo = SimpleUploadedFile('imagem.png', b'\x89PNG\r\n\x1a\nconteudo', content_type='image/png')
		self.assertIs(validar_upload(arquivo), arquivo)

	def test_rejeita_office_com_conteudo_que_nao_e_zip(self):
		from core.file_validation import validar_upload
		with self.assertRaisesMessage(ValidationError, 'arquivo Office válido'):
			validar_upload(SimpleUploadedFile(
				'documento.docx', b'nao e zip',
				content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
			))

	def test_preserva_posicao_do_arquivo_apos_validacao(self):
		from core.file_validation import validar_upload
		arquivo = SimpleUploadedFile('arquivo.txt', b'conteudo', content_type='text/plain')
		arquivo.read(2)
		posicao = arquivo.tell()

		validar_upload(arquivo)

		self.assertEqual(arquivo.tell(), posicao)

	def test_rejeita_documento_office_com_macro(self):
		import io
		import zipfile
		from core.file_validation import validar_upload
		conteudo = io.BytesIO()
		with zipfile.ZipFile(conteudo, 'w') as pacote:
			pacote.writestr('word/vbaProject.bin', b'projeto VBA')
		arquivo = SimpleUploadedFile(
			'documento.docx', conteudo.getvalue(),
			content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
		)
		with self.assertRaisesMessage(ValidationError, 'macros não são permitidos'):
			validar_upload(arquivo)

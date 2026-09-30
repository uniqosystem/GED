import io
import tempfile
import zipfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from core.models import LogAuditoria
from ecarta.models import ConfiguracaoEcarta, LoteEcarta
from ecarta.services import gerar_lote, persistir_lote


CSV_COMPLETO = (
    'NOME;ENDEREÇO;NÚM. ENDEREÇO;END. COMPLEMENTO;BAIRRO;CIDADE;UF;CEP\n'
    'Maria Silva;Rua Central;10;Sala 2;Centro;João Pessoa;PB;58000000\n'
)


@override_settings(UPLOAD_MAX_SIZE=1024 * 1024)
class EcartaServiceTests(TestCase):
    def criar_csv(self, conteudo):
        return SimpleUploadedFile(
            'enderecos.csv',
            conteudo.encode('latin1'),
            content_type='text/csv',
        )

    def test_gera_lote_e_conteudos_esperados(self):
        resultado = gerar_lote(self.criar_csv(CSV_COMPLETO))

        self.assertEqual(resultado['lote'], '16')
        self.assertIn('0077383354', resultado['conteudo_servico'])
        self.assertIn('Maria Silva|Rua Central|10|Sala 2|Centro|João Pessoa|PB|58000000', resultado['conteudo_servico'])
        self.assertEqual(resultado['conteudo_resposta'], '1|16|A\n')
        self.assertRegex(resultado['nome_resposta'], r'^e-Carta_55944_16_Resposta\d{14}\.txt$')
        self.assertEqual(ConfiguracaoEcarta.objects.get(pk=1).ultimo_lote, 16)

    def test_rejeita_colunas_obrigatorias_ausentes(self):
        arquivo = self.criar_csv('NOME;CIDADE\nMaria Silva;João Pessoa\n')

        with self.assertRaisesRegex(ValueError, 'não foram encontradas'):
            gerar_lote(arquivo)

        self.assertFalse(ConfiguracaoEcarta.objects.filter(pk=1).exists())

    def test_persiste_arquivos_em_subpasta_e_registra_auditoria(self):
        usuario = User.objects.create_user('ecarta_arquivo', password='senha')
        resultado = gerar_lote(self.criar_csv(CSV_COMPLETO))

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(ECARTA_DIR=media_dir):
                lote = persistir_lote(resultado, usuario)

                self.assertTrue(lote.arquivo_servico.name.startswith(f'lotes/{lote.numero_lote}/'))
                self.assertTrue(lote.arquivo_resposta.name.startswith(f'lotes/{lote.numero_lote}/'))
                with lote.arquivo_servico.open('rb') as arquivo:
                    self.assertIn(b'Maria Silva', arquivo.read())

        log = LogAuditoria.objects.get(acao='GERAR_ECARTA')
        self.assertEqual(log.usuario, usuario)
        self.assertIn(lote.numero_lote, log.descricao)


class EcartaDownloadTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('ecarta_teste', password='senha')
        self.usuario.perfil.password_changed = True
        self.usuario.perfil.save(update_fields=['password_changed'])
        self.client.force_login(self.usuario)
        session = self.client.session
        session['ecarta_servico'] = 'linha de servico'
        session['ecarta_resposta'] = 'linha de resposta\n'
        session['ecarta_lote'] = '16'
        session['ecarta_nome_resposta'] = 'resposta.txt'
        session.save()

    def ler_zip(self, response):
        with zipfile.ZipFile(io.BytesIO(response.content)) as pacote:
            nome = pacote.namelist()[0]
            return nome, pacote.read(nome).decode()

    def test_baixa_arquivo_de_servico_em_zip(self):
        response = self.client.get('/ecarta/baixar/servico/')

        self.assertEqual(response.status_code, 200)
        nome, conteudo = self.ler_zip(response)
        self.assertEqual(nome, 'e-Carta_55944_16_servico.txt')
        self.assertEqual(conteudo, 'linha de servico')
        self.assertTrue(LogAuditoria.objects.filter(
            usuario=self.usuario,
            acao='BAIXAR_ECARTA_SERVICO',
        ).exists())

    def test_baixa_arquivo_de_resposta_em_zip(self):
        response = self.client.get('/ecarta/baixar/resposta/')

        self.assertEqual(response.status_code, 200)
        nome, conteudo = self.ler_zip(response)
        self.assertEqual(nome, 'resposta.txt')
        self.assertEqual(conteudo, 'linha de resposta\n')
        self.assertTrue(LogAuditoria.objects.filter(
            usuario=self.usuario,
            acao='BAIXAR_ECARTA_RESPOSTA',
        ).exists())


class EcartaHttpTests(TestCase):
    def test_geracao_exige_autenticacao(self):
        response = self.client.get('/ecarta/gerar/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/?next=/ecarta/gerar/', response.url)

    def test_post_sem_arquivo_nao_cria_lote(self):
        usuario = User.objects.create_user('ecarta_http', password='senha')
        usuario.perfil.password_changed = True
        usuario.perfil.save(update_fields=['password_changed'])
        self.client.force_login(usuario)

        response = self.client.post('/ecarta/gerar/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/ecarta/gerar/')
        self.assertFalse(ConfiguracaoEcarta.objects.filter(pk=1).exists())

    def test_post_de_conversao_persiste_lote_e_auditoria(self):
        usuario = User.objects.create_user('ecarta_http_arquivo', password='senha')
        usuario.perfil.password_changed = True
        usuario.perfil.save(update_fields=['password_changed'])
        self.client.force_login(usuario)
        arquivo = SimpleUploadedFile(
            'enderecos.csv',
            CSV_COMPLETO.encode('latin1'),
            content_type='text/csv',
        )

        with tempfile.TemporaryDirectory() as media_dir:
            with override_settings(ECARTA_DIR=media_dir):
                response = self.client.post('/ecarta/gerar/', {'arquivo_csv': arquivo})

                self.assertEqual(response.status_code, 200)
                lote = LoteEcarta.objects.get(criado_por=usuario)
                self.assertTrue(lote.arquivo_servico.storage.exists(lote.arquivo_servico.name))
                self.assertTrue(lote.arquivo_resposta.storage.exists(lote.arquivo_resposta.name))
                self.assertTrue(LogAuditoria.objects.filter(
                    usuario=usuario,
                    acao='GERAR_ECARTA',
                ).exists())

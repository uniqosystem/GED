import importlib.util
import threading
import time
import unittest

from django.contrib.auth.models import User
from django.test import LiveServerTestCase

from core.models import Setor

from .models import Tramitacao


PLAYWRIGHT_AVAILABLE = importlib.util.find_spec('playwright') is not None

if PLAYWRIGHT_AVAILABLE:
    from playwright.sync_api import sync_playwright


@unittest.skipUnless(
    PLAYWRIGHT_AVAILABLE,
    'Playwright não está instalado; instale as dependências E2E para executar este teste.',
)
class TramitationBrowserTests(LiveServerTestCase):
    def setUp(self):
        self.setor_origem = Setor.objects.create(nome='Browser Origem', caminho_rede='C:\\GED\\Browser Origem')
        self.setor_destino = Setor.objects.create(nome='Browser Destino', caminho_rede='C:\\GED\\Browser Destino')
        self.remetente = User.objects.create_user('browser_remetente', password='senha')
        self.destinatario = User.objects.create_user('browser_destinatario', password='senha')
        self.outro_usuario = User.objects.create_user('browser_outro', password='senha')
        for usuario in (self.remetente, self.destinatario, self.outro_usuario):
            usuario.perfil.password_changed = True
            usuario.perfil.save()
        self.remetente.perfil.setor = self.setor_origem
        self.remetente.perfil.save()
        self.destinatario.perfil.setor = self.setor_destino
        self.destinatario.perfil.save()
        self.outro_usuario.perfil.setor = self.setor_destino
        self.outro_usuario.perfil.save()
        self.tramitacao = Tramitacao.objects.create(
            protocolo='BROWSER-0001', criador=self.remetente, remetente=self.remetente,
            setor_origem=self.setor_origem, setor_destino=self.setor_destino,
            usuario_destino=self.destinatario, titulo='Tramitação de navegador',
            despacho='Despacho para teste E2E', status='PENDENTE', aguardar_resposta=True,
        )

    def executar_no_navegador(self, callback, usuario='browser_destinatario'):
        resultado = {}

        def executar():
            browser = None
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_default_timeout(5000)
                    page.goto(f'{self.live_server_url}/', wait_until='domcontentloaded', timeout=20000)
                    page.get_by_placeholder('Usuário').fill(usuario)
                    page.get_by_placeholder('Senha').fill('senha')
                    page.get_by_role('button', name='Entrar').click()
                    page.goto(f'{self.live_server_url}/tramitacao/caixa-de-entrada/', wait_until='domcontentloaded', timeout=20000)
                    callback(page)
            except Exception as exc:
                resultado['erro'] = repr(exc)
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

        thread = threading.Thread(target=executar)
        thread.start()
        thread.join(timeout=45)
        self.assertFalse(thread.is_alive(), 'O teste do navegador excedeu 45 segundos.')
        self.assertNotIn('erro', resultado, resultado.get('erro'))

    def abrir_detalhes_no_navegador(self, page):
        page.get_by_role('button', name='Visualizar').first.click()
        page.locator('#modalDetalhesTramitacao').wait_for(state='visible')

    def aguardar_status(self, status, despacho=None, timeout=5):
        limite = time.monotonic() + timeout
        while time.monotonic() < limite:
            self.tramitacao.refresh_from_db()
            if self.tramitacao.status == status and (despacho is None or self.tramitacao.despacho == despacho):
                return
            time.sleep(0.1)
        self.tramitacao.refresh_from_db()

    def test_destinatario_abre_detalhes_e_modal_de_resposta(self):
        resultado = {}

        def executar_navegador():
            browser = None
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.set_default_timeout(5000)
                    page.goto(f'{self.live_server_url}/', wait_until='domcontentloaded', timeout=10000)
                    page.get_by_placeholder('Usuário').fill('browser_destinatario')
                    page.get_by_placeholder('Senha').fill('senha')
                    page.get_by_role('button', name='Entrar').click()
                    page.goto(f'{self.live_server_url}/tramitacao/caixa-de-entrada/', wait_until='domcontentloaded', timeout=10000)
                    page.get_by_role('button', name='Visualizar').wait_for(timeout=5000)
                    page.get_by_role('button', name='Visualizar').click()
                    page.locator('#modalDetalhesTramitacao').get_by_role('button', name='Receber').click()
                    page.locator('#modalResponderTramitacao').wait_for(state='visible', timeout=5000)
                    resultado['detalhes'] = page.locator('#modalDetalhesTramitacao.show').count() == 0
                    resultado['resposta'] = page.get_by_role('button', name='Enviar Resposta').is_visible()
                    resultado['aguardar'] = page.get_by_label('Aguardar resposta deste setor?').is_visible()
            except Exception as exc:
                resultado['erro'] = repr(exc)
            finally:
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

        thread = threading.Thread(target=executar_navegador)
        thread.start()
        thread.join(timeout=30)
        self.assertFalse(thread.is_alive(), 'O teste do navegador excedeu 30 segundos.')
        self.assertNotIn('erro', resultado, resultado.get('erro'))
        self.assertTrue(resultado.get('detalhes'))
        self.assertTrue(resultado.get('resposta'))
        self.assertTrue(resultado.get('aguardar'))

    def test_destinatario_devolve_tramitacao_pelo_navegador(self):
        def executar_fluxo(page):
            self.abrir_detalhes_no_navegador(page)
            with page.expect_navigation(wait_until='networkidle', timeout=10000):
                page.locator('#modalDetalhesTramitacao').get_by_role('button', name='Devolver').click()
        self.executar_no_navegador(executar_fluxo)
        self.aguardar_status('DEVOLVIDO')
        self.tramitacao.refresh_from_db()
        self.assertEqual(self.tramitacao.status, 'DEVOLVIDO')

    def test_outro_usuario_do_setor_nao_visualiza_tramitacao_direcionada(self):
        def verificar_acesso(page):
            page.locator('#aba-recebidos').wait_for(state='visible')
            self.assertFalse(page.locator('#aba-recebidos').get_by_role('button', name='Visualizar').count())
            self.assertNotIn(self.tramitacao.protocolo, page.locator('#aba-recebidos').inner_text())
        self.executar_no_navegador(verificar_acesso, usuario='browser_outro')

    def test_destinatario_responde_e_conclui_pelo_navegador(self):
        def executar_fluxo(page):
            self.abrir_detalhes_no_navegador(page)
            page.locator('#modalDetalhesTramitacao').get_by_role('button', name='Receber').click()
            page.locator('#modalResponderTramitacao').wait_for(state='visible')
            page.locator('#formResponder').get_by_role('button', name='Enviar Resposta').wait_for(state='visible')
            page.locator('#respDespacho').fill('Resposta final pelo navegador')
            page.locator('#respAguardarResposta').uncheck(force=True)
            with page.expect_navigation(wait_until='domcontentloaded', timeout=10000):
                page.locator('#formResponder').get_by_role('button', name='Enviar Resposta').click()
        self.executar_no_navegador(executar_fluxo)
        self.aguardar_status('CONCLUIDO')
        self.assertEqual(self.tramitacao.status, 'CONCLUIDO')
        self.assertEqual(self.tramitacao.despacho, 'Resposta final pelo navegador')

    def test_destinatario_responde_aguardando_novo_retorno_pelo_navegador(self):
        def executar_fluxo(page):
            self.abrir_detalhes_no_navegador(page)
            page.locator('#modalDetalhesTramitacao').get_by_role('button', name='Receber').click()
            page.locator('#modalResponderTramitacao').wait_for(state='visible')
            page.locator('#respDespacho').fill('Solicitação de novo retorno pelo navegador')
            page.locator('#respAguardarResposta').check()
            with page.expect_navigation(wait_until='domcontentloaded', timeout=10000):
                page.get_by_role('button', name='Enviar Resposta').click()
        self.executar_no_navegador(executar_fluxo)
        self.tramitacao.refresh_from_db()
        self.assertEqual(self.tramitacao.status, 'PENDENTE')
        self.aguardar_status('PENDENTE', despacho='Solicitação de novo retorno pelo navegador')
        self.assertEqual(self.tramitacao.despacho, 'Solicitação de novo retorno pelo navegador')
        self.assertEqual(self.tramitacao.setor_destino_id, self.setor_origem.id)

    def test_remetente_edita_e_reenvia_devolucao_pelo_navegador(self):
        def executar_fluxo(page):
            self.abrir_detalhes_no_navegador(page)
            with page.expect_navigation(wait_until='domcontentloaded', timeout=10000):
                page.locator('#modalDetalhesTramitacao').get_by_role('button', name='Devolver').click()
            page.goto(f'{self.live_server_url}/logout/', wait_until='domcontentloaded', timeout=10000)
            page.get_by_placeholder('Usuário').fill('browser_remetente')
            page.get_by_placeholder('Senha').fill('senha')
            page.get_by_role('button', name='Entrar').click()
            page.goto(f'{self.live_server_url}/tramitacao/caixa-de-entrada/', wait_until='domcontentloaded', timeout=10000)
            page.get_by_role('tab', name='Enviados').click()
            page.locator('#aba-enviados').wait_for(state='visible')
            page.locator('#aba-enviados').get_by_role('button', name='Visualizar').first.wait_for(state='visible')
            self.abrir_detalhes_no_navegador(page)
            botao_editar = page.locator('#modalDetalhesTramitacao').get_by_role('link', name='Editar / Reenviar')
            botao_editar.wait_for(state='visible')
            botao_editar.click()
            page.locator('#modalEditarTramitacao').wait_for(state='visible')
            form_edicao = page.locator('#formEditarTramitacao')
            form_edicao.locator('#id_tipo_documento').select_option('OFICIO')
            form_edicao.locator('#id_titulo').fill('Tramitação corrigida')
            form_edicao.locator('#id_setor_destino').select_option(str(self.setor_destino.id))
            form_edicao.locator('#id_despacho').fill('Despacho corrigido pelo navegador')
            with page.expect_navigation(wait_until='domcontentloaded', timeout=10000):
                form_edicao.get_by_role('button', name='Salvar e Reenviar').click()
        self.executar_no_navegador(executar_fluxo)
        self.aguardar_status('PENDENTE')
        self.tramitacao.refresh_from_db()
        self.assertEqual(self.tramitacao.status, 'PENDENTE')
        self.assertEqual(self.tramitacao.titulo, 'Tramitação corrigida')
        self.assertEqual(self.tramitacao.despacho, 'Despacho corrigido pelo navegador')

    def test_assinatura_obrigatoria_e_executada_pelo_navegador(self):
        self.tramitacao.aguardar_resposta = False
        self.tramitacao.exige_assinatura = True
        self.tramitacao.save(update_fields=['aguardar_resposta', 'exige_assinatura'])
        def executar_fluxo(page):
            self.abrir_detalhes_no_navegador(page)
            page.locator('#modalDetalhesTramitacao').get_by_role('button', name='Receber').click()
            page.locator('#modalAssinatura').wait_for(state='visible')
            page.locator('#senha_confirmacao').fill('senha')
            with page.expect_navigation(wait_until='domcontentloaded', timeout=10000):
                page.locator('#modalAssinatura').get_by_role('button', name='Assinar e Concluir').click()
        self.executar_no_navegador(executar_fluxo)
        self.tramitacao.refresh_from_db()
        self.assertTrue(self.tramitacao.assinado)
        self.assertEqual(self.tramitacao.status, 'RECEBIDO')

    def test_assinatura_e_resposta_combinadas_pelo_navegador(self):
        self.tramitacao.exige_assinatura = True
        self.tramitacao.save(update_fields=['exige_assinatura'])
        def executar_fluxo(page):
            self.abrir_detalhes_no_navegador(page)
            page.locator('#modalDetalhesTramitacao').get_by_role('button', name='Receber').click()
            page.locator('#modalAssinatura').wait_for(state='visible')
            page.locator('#senha_confirmacao').fill('senha')
            with page.expect_navigation(wait_until='domcontentloaded', timeout=10000):
                page.locator('#modalAssinatura').get_by_role('button', name='Assinar e Concluir').click()
            page.goto(f'{self.live_server_url}/tramitacao/caixa-de-entrada/', wait_until='networkidle', timeout=20000)
            page.locator('#recebidos').wait_for(state='visible')
            page.locator('#aba-recebidos').get_by_role('button', name='Visualizar').first.wait_for(state='visible')
            self.abrir_detalhes_no_navegador(page)
            page.locator('#modalDetalhesTramitacao').get_by_role('button', name='Responder').click()
            page.locator('#modalResponderTramitacao').wait_for(state='visible')
            page.locator('#respDespacho').fill('Resposta assinada pelo navegador')
            page.locator('#respAguardarResposta').uncheck(force=True)
            with page.expect_navigation(wait_until='domcontentloaded', timeout=10000):
                page.locator('#formResponder').get_by_role('button', name='Enviar Resposta').click()
        self.executar_no_navegador(executar_fluxo)
        self.tramitacao.refresh_from_db()
        self.assertTrue(self.tramitacao.assinado)
        self.aguardar_status('CONCLUIDO', despacho='Resposta assinada pelo navegador')
        self.assertEqual(self.tramitacao.status, 'CONCLUIDO')
        self.assertEqual(self.tramitacao.despacho, 'Resposta assinada pelo navegador')

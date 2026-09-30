from django.urls import path, include
from . import views
from . import auth_views
from . import file_views
from . import storage_views
from . import navigation_views
from . import trash_views
from . import audit_views

urlpatterns = [
    path('navegar/excluir-multiplos-ajax/', trash_views.excluir_multiplos_ajax, name='excluir_multiplos_ajax'),
    path('navegar/<str:modulo>/', navigation_views.navegar_pastas, name='navegar_pastas'),
    path('', auth_views.inicio, name='inicio'),
    path('health/', auth_views.health_check, name='health_check'),
    path('alterar-senha/', auth_views.change_password, name='change_password'),
    path('inicio/', auth_views.pagina_inicial_direcionamento, name='inicio_sistema'),
    path('perfil/', auth_views.perfil_usuario, name='perfil_usuario'),
    path('busca/', navigation_views.busca_crf, name='busca_crf'),
    path('visualizar/', file_views.visualizar_arquivo, name='visualizar_arquivo'), 
    path('baixar/', file_views.baixar_arquivo, name='baixar_arquivo'), 
    path('renomear/', file_views.renomear_arquivo, name='renomear_arquivo'),
    path('apagar/', trash_views.apagar_arquivo, name='apagar_arquivo'),
    path('upload-geral/', storage_views.upload_arquivo_geral, name='upload_arquivo_geral'),
    path('criar-pasta/', storage_views.criar_subpasta, name='criar_subpasta'),
    path('lixeira/', trash_views.ver_lixeira, name='ver_lixeira'),
    path('lixeira/restaurar/', trash_views.restaurar_arquivo, name='restaurar_arquivo'),
    path('lixeira/esvaziar/', trash_views.esvaziar_lixeira, name='esvaziar_lixeira'),
    path('auditoria/', audit_views.ver_auditoria, name='ver_auditoria'),
    path('upload-multiplo-ajax/', storage_views.upload_multiplo_ajax, name='upload_multiplo_ajax'),
    path('auditoria/exportar/', audit_views.exportar_auditoria, name='exportar_auditoria'),
    path('logout/', auth_views.logout_usuario, name='logout'),
]
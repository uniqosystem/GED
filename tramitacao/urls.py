from django.urls import path

from . import api_views
from . import action_views
from . import inbox_views

urlpatterns = [
    path('caixa-de-entrada/', inbox_views.caixa_entrada, name='caixa_entrada'),
    path('nova/', inbox_views.nova_tramitacao, name='url_nova_tramitacao'),
    path('<int:pk>/receber/', action_views.receber_tramitacao, name='receber_tramitacao'),
    path('<int:pk>/finalizar/', action_views.finalizar_tramitacao, name='finalizar_tramitacao'),
    path('<int:pk>/devolver/', action_views.devolver_tramitacao, name='devolver_tramitacao'),
    path('<int:pk>/anexos/', api_views.listar_anexos_json, name='listar_anexos_json'),
    path('<int:pk>/responder/', action_views.responder_tramitacao, name='responder_tramitacao'),
    path('<int:pk>/api-historico/', api_views.api_historico_tramitacao, name='api_historico_tramitacao'),
    path('<int:pk>/editar/', action_views.editar_tramitacao, name='editar_tramitacao'),
    path('<int:pk>/excluir/', action_views.excluir_tramitacao_devolvida, name='excluir_tramitacao'),
    path('<int:tramitacao_id>/assinar/', action_views.assinar_tramitacao, name='assinar_tramitacao'),
    path('ajax/usuarios-setores/', api_views.ajax_usuarios_setores, name='ajax_usuarios_setores'),
    path('verificar-notificacoes/', api_views.verificar_notificacoes, name='verificar_notificacoes'),
]
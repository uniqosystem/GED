from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='registrar_ponto', permanent=False)),
    path('registrar/', views.registrar_ponto, name='registrar_ponto'),
    path('perfil/', views.meu_perfil, name='meu_perfil'),
    path('relatorio/', views.pagina_relatorio, name='pagina_relatorio'),
    path('exportar/', views.exportar_ponto, name='exportar_ponto'),
    path('historico/', views.meu_historico, name='meu_historico'),
    path('editar-ponto/<int:id>/', views.editar_ponto, name='editar_ponto'),
    path('rh/', views.painel_rh, name='painel_rh'),
    path('rh/dashboard/', views.dashboard_presenca, name='dashboard_presenca'),
    path('rh/funcionarios/', views.lista_funcionarios, name='lista_funcionarios'),
    path('rh/editar/<int:user_id>/', views.editar_funcionario_rh, name='editar_funcionario_rh'),
    path('ocorrencias/', views.listar_ocorrencias, name='listar_ocorrencias'),
    path('ocorrencias/editar/<int:pk>/', views.editar_ocorrencia, name='editar_ocorrencia'),
    path('ocorrencias/apagar/<int:pk>/', views.apagar_ocorrencia, name='apagar_ocorrencia'),
    path('ocorrencias/nova/', views.registrar_ocorrencia, name='registrar_ocorrencia'),
    path('apagar/<int:ponto_id>/', views.apagar_ponto, name='apagar_ponto'),
    path('upload-contracheque/', views.upload_contracheque, name='upload_contracheque'),
    path('excluir-contracheque/<int:contracheque_id>/', views.excluir_contracheque, name='excluir_contracheque'),
]
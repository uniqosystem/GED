from django.urls import path

from . import views

app_name = 'eventos'

urlpatterns = [
	path('gestao/', views.gestao_lista, name='gestao_lista'),
	path('gestao/criar/', views.gestao_criar, name='gestao_criar'),
	path('gestao/<int:pk>/editar/', views.gestao_editar, name='gestao_editar'),
	path('gestao/<int:pk>/inscricoes/', views.gestao_inscricoes, name='gestao_inscricoes'),
	path('gestao/<int:pk>/presencas/', views.gestao_presencas, name='gestao_presencas'),
	path('gestao/inscricao/<int:pk>/certificado/', views.gestao_gerar_certificado, name='gestao_gerar_certificado'),
	path('', views.lista_eventos, name='lista'),
	path('<slug:slug>/', views.detalhe_evento, name='detalhe'),
	path('<slug:slug>/inscricao/', views.inscrever_evento, name='inscricao'),
	path('<slug:slug>/inscricao/sucesso/', views.inscricao_sucesso, name='inscricao_sucesso'),
]

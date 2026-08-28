from django.urls import path
from . import views
from . import download_views

urlpatterns = [
    path('gerar/', views.gerar_ecarta, name='gerar_ecarta'),
    path('baixar/servico/', download_views.baixar_servico, name='baixar_servico'),
    path('baixar/resposta/', download_views.baixar_resposta, name='baixar_resposta'),
]
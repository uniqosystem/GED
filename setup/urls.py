from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

from .media_views import private_media

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.svg', permanent=False)),
    # ged
    path('admin/', admin.site.urls),
    path('', include('core.urls')), 

    # tramitacao
    path('tramitacao/', include('tramitacao.urls')),

    # ecarta
    path('ecarta/', include('ecarta.urls')),

    # ponto
    path('ponto/', include('ponto.urls')),

    # eventos
    path('eventos/', include('eventos.urls')),
    path('media/<path:path>', private_media, name='private_media'),
]
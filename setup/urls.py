from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ged
    path('admin/', admin.site.urls),
    path('', include('core.urls')), 

    # tramitacao
    path('tramitacao/', include('tramitacao.urls')),

    # ecarta
    path('ecarta/', include('ecarta.urls')),
]

# AQUI é onde você corrige os erros 404 do CSS/JS
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
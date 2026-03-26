from django.urls import path
from .views import CustomPasswordResetView
from django.views.generic import TemplateView
from . import views
urlpatterns = [
    path('recuperar/', CustomPasswordResetView.as_view(), name='recuperar'),

    path('recuperar_enviado/',
         TemplateView.as_view(template_name='usuarios/recuperar_enviado.html'),
         name='recuperar_enviado'),
    path('registrar/', views.registrar_personal, name='registrar_personal'),
    path('lista/', views.lista_personal, name='lista_personal'),
]
from django.urls import path
from .views import CustomPasswordResetView
from django.views.generic import TemplateView

urlpatterns = [
    path('recuperar/', CustomPasswordResetView.as_view(), name='recuperar'),

    path('recuperar_enviado/',
         TemplateView.as_view(template_name='usuarios/recuperar_enviado.html'),
         name='recuperar_enviado'),
]
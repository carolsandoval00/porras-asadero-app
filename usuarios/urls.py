from django.urls import path
from . import views
from django.urls import path
from .views import DetalleUsuarioView
from .views import CustomPasswordResetView
from django.views.generic import TemplateView
from . import views

from .views import inicio_usuarios, actualizar_usuarios

urlpatterns = [
    path('', inicio_usuarios, name='inicio_usuarios'),
    path('actualizar/<int:id>/', actualizar_usuarios, name='actualizar_usuarios'),
    path('inactivar/', views.inactivar_usuario, name='inactivar_usuario'),
    path('', inicio_usuarios, name='inicio_usuarios'), 
    path('consultar/<int:pk>/', DetalleUsuarioView.as_view(), name='detalle_usuario'),

    path('recuperar/', CustomPasswordResetView.as_view(), name='recuperar'),

    path('recuperar_enviado/',
         TemplateView.as_view(template_name='usuarios/recuperar_enviado.html'),
         name='recuperar_enviado'),
    path('registrar/', views.registrar_personal, name='registrar_personal'),
    path('lista/', views.lista_personal, name='lista_personal'),

]
from django.urls import path
# from .views import inicio_usuarios, actualizar_usuarios, validar_permisos, redireccion_post_login
from django.contrib.auth import views as auth_views
from . import views
from django.urls import path
# from .views import DetalleUsuarioView
# from .views import CustomPasswordResetView
from django.views.generic import TemplateView
from . import views
# from .views import inicio_usuarios, actualizar_usuarios


from .views import acceder_sistema
from .views import consultar_usuario

urlpatterns = [
    path('consultar/', consultar_usuario, name='consultar_usuario'),
]

urlpatterns = [
    # path('', inicio_usuarios, name='inicio_usuarios'),
    # path('actualizar_usuario/<int:id>/', actualizar_usuarios, name='actualizar_usuario'),
    # path('validar_permisos/', validar_permisos, name='validar_permisos'),
    
    # path('redireccion/', redireccion_post_login, name='redireccion'),

    
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    # path('actualizar/<int:id>/', actualizar_usuarios, name='actualizar_usuarios'),
    # path('inactivar/', views.inactivar_usuario, name='inactivar_usuario'),
    # path('', inicio_usuarios, name='inicio_usuarios'), 
    # path('consultar/<int:pk>/', DetalleUsuarioView.as_view(), name='detalle_usuario'),

    # path('recuperar/', CustomPasswordResetView.as_view(), name='recuperar'),

    path('recuperar_enviado/',
         TemplateView.as_view(template_name='usuarios/recuperar_enviado.html'),
         name='recuperar_enviado'),
    # path('registrar/', views.registrar_personal, name='registrar_personal'),
    # path('lista/', views.lista_personal, name='lista_personal'),

    # Autenticación
    path('acceder/', acceder_sistema, name='acceder_sistema'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('recuperar/', CustomPasswordResetView.as_view(), name='recuperar'),
    path(
        'recuperar_enviado/',
        TemplateView.as_view(template_name='usuarios/recuperar_enviado.html'),
        name='recuperar_enviado'
    ),
]
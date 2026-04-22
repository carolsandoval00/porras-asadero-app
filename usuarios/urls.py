from django.urls import path
from django.contrib.auth import views as auth_views
from . import views 

urlpatterns = [
    # 1. LA RAÍZ PRIMERO: Es el Panel de Control/Dashboard

    # 2. AUTENTICACIÓN
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'), # Asegúrate de tener esta para poder salir
    path('acceder/', views.acceder_sistema, name='acceder_sistema'),
    path('redireccion/', views.redireccion_post_login, name='redireccion'),
    
    # 3. GESTIÓN DE PERSONAL
    path('lista/', views.lista_personal, name='lista_personal'),
    path('registrar/', views.registrar_personal, name='registrar_personal'),
    path('consultar/', views.consultar_usuario, name='consultar_usuario'),
    path('actualizar/<int:id>/', views.actualizar_usuarios, name='actualizar_usuarios'),
    path('inactivar/', views.inactivar_usuario, name='inactivar_usuario'),
    
    # 4. RECUPERACIÓN DE CONTRASEÑA
    path('recuperar/', auth_views.PasswordResetView.as_view(
        template_name='usuarios/login.html',
        extra_context={'vista': 'recuperar'}
    ), name='password_reset'),
    
    path('recuperar_enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='usuarios/login.html',
        extra_context={'vista': 'recuperar_enviado'}
    ), name='password_reset_done'),

    # Estas son necesarias para que el flujo de Django de recuperar contraseña no de error 404
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='usuarios/login.html',
        extra_context={'vista': 'recuperar_confirmar'}
    ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='usuarios/login.html',
        extra_context={'vista': 'recuperar_terminado'}
    ), name='password_reset_complete'),
]
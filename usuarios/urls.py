from django.urls import path
from django.contrib.auth import views as auth_views
from . import views 

urlpatterns = [
    # 1. AUTENTICACIÓN
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('acceder/', views.acceder_sistema, name='acceder_sistema'),
    path('redireccion/', views.redireccion_post_login, name='redireccion'),
    
    # 2. GESTIÓN DE PERSONAL
    path('lista/', views.lista_personal, name='lista_personal'),
    path('registrar/', views.registrar_personal, name='registrar_personal'),
    path('perfil/', views.panel_perfil, name='panel_perfil'),           # <-- antes: consultar/
    path('actualizar/<int:id>/', views.actualizar_usuarios, name='actualizar_usuarios'),
    path('inactivar/', views.inactivar_usuario, name='inactivar_usuario'),
    
    # 3. RECUPERACIÓN DE CONTRASEÑA
    path('recuperar/', auth_views.PasswordResetView.as_view(
        template_name='usuarios/login.html',
        extra_context={'vista': 'recuperar'}
    ), name='password_reset'),
    
    path('recuperar_enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='usuarios/login.html',
        extra_context={'vista': 'recuperar_enviado'}
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='usuarios/login.html',
        extra_context={'vista': 'recuperar_confirmar'}
    ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='usuarios/login.html',
        extra_context={'vista': 'recuperar_terminado'}
    ), name='password_reset_complete'),
]
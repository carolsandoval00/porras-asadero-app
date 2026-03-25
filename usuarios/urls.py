from django.urls import path
from .views import inicio_usuarios, actualizar_usuarios, validar_permisos
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', inicio_usuarios, name='inicio_usuarios'),
    path('actualizar_usuario/<int:id>/', actualizar_usuarios, name='actualizar_usuario'),
    path('validar_permisos/', validar_permisos, name='validar_permisos'),

    # 🔐 login
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
]
from django.urls import path
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('recuperar/', auth_views.PasswordResetView.as_view(
        template_name='usuarios/recuperar.html'  # 👈 tu template
    ), name='recuperar'),
]
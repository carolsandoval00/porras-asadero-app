from django.urls import path
from django.contrib.auth import views as auth_views
from usuarios.views import *

urlpatterns = [
    path('', inicio_usuarios, name='inicio_usuarios'),
    path('recuperar/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('recuperar/enviado/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/completo/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'), 
]

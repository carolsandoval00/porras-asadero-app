from django.urls import path
from .views import inicio_usuarios, actualizar_usuarios

urlpatterns = [
    path('', inicio_usuarios, name='inicio_usuarios'),
    path('actualizar/<int:id>/', actualizar_usuarios, name='actualizar_usuarios'),
]
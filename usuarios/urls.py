from django.contrib import admin
from usuarios.views import *

from django.urls import path

urlpatterns = [
    path('', inicio_usuarios, name='inicio_usuarios'),
    path('actualizar_usuario/<int:id>/', actualizar_usuarios, name='actualizar_usuario'),
] 
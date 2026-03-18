from django.contrib import admin
from django.urls import path 

from usuarios.views import *
from django.urls import path
from .views import *

urlpatterns = [
    path('', inicio_usuarios, name='inicio_usuarios'),
    path('actualizar_usuarios/<int:id>/', actualizar_usuarios, name='actualizar_usuarios'),
]
from django.contrib import admin
from django.urls import path 

from usuarios.views import *

urlpatterns = [
    path('', inicio_usuarios, name='inicio_usuarios'), 
]
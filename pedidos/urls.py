from django.contrib import admin
from django.urls import path 

from pedidos.views import *

urlpatterns = [
    path('', inicio_pedidos, name='inicio_pedidos'), 
]
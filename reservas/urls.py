from django.contrib import admin
from django.urls import path 

from reservas.views import *

urlpatterns = [
    path('', inicio_reservas, name='inicio_reservas'), 
]
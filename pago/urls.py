from django.contrib import admin
from django.urls import path 

from pago.views import *

urlpatterns = [
    path('', inicio_pago, name='inicio_pago'), 
]
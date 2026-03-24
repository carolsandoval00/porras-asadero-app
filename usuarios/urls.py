from django.contrib import admin
from django.urls import path 

from usuarios.views import *

urlpatterns = [
    path('', inicio_usuarios, name='inicio_usuarios'), 
<<<<<<< Updated upstream
=======
]

from django.urls import path
from .views import DetalleUsuarioView

urlpatterns = [
    # El <int:pk> es fundamental para saber qué usuario consultar
    path('consultar/<int:pk>/', DetalleUsuarioView.as_view(), name='detalle_usuario'),
>>>>>>> Stashed changes
]
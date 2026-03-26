from django.urls import path
from . import views

urlpatterns = [
    path('inactivar/', views.inactivar_usuario, name='inactivar_usuario'),
]
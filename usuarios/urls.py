from django.urls import path
from . import views

urlpatterns = [
    path('eliminar/', views.eliminar_usuario, name='eliminar_usuario'),
]
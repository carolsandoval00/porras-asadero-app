from django.urls import path
from . import views

urlpatterns = [
    path('eliminar-detalle/', views.eliminar_detalle, name='eliminar_detalle'),
]
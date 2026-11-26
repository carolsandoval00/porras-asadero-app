from django.urls import path
from . import views

app_name = 'backup'

urlpatterns = [
    path('', views.backup, name='backup'),
    path('restaurar/', views.restaurar_datos, name='restaurar_datos'),
]

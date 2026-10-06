from django.urls import path
from . import views


app_name = 'ayuda'

urlpatterns = [
    path('', views.centroayuda, name='centro_ayuda'),
]


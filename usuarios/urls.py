from django.urls import path
from . import views

urlpatterns = [
    path('registrar/', views.registrar_personal, name='registrar_personal'),
    path('lista/', views.lista_personal, name='lista_personal'),
]
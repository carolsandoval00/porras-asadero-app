from django.urls import path
from . import views

urlpatterns = [
    path('mesa/editar/', views.actualizar_mesa, name='actualizar_mesa'),
]
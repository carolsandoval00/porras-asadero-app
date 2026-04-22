from django.urls import path
from . import views

urlpatterns = [
    # Ruta base para Reservas y Mesas
    path('', views.reserva_view, name='reserva_inicio'),
    
    # Otras rutas
    path('mesa/editar/', views.actualizar_mesa, name='actualizar_mesa'),
    path('detalle/eliminar/', views.eliminar_detalle, name='eliminar_detalle'),
]
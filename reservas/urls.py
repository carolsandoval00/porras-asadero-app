from django.urls import path
from . import views

urlpatterns = [
    # Inicio
    path('', views.reserva_view, name='reserva_inicio'),

    # Reservas
    path('crear/', views.crear_reserva, name='crear_reserva'),
    path('detalle/eliminar/', views.eliminar_detalle, name='eliminar_detalle'),

    # Mesas
    path('mesas/diagrama/', views.diagrama_mesas, name='diagrama_mesas'),
    path('mesas/nueva/', views.gestion_mesas, name='gestion_mesas'),
    path('mesa/listar/', views.listar_mesas_vista, name='listar_mesas'),
    path('mesa/editar/<int:mesa_id>/', views.actualizar_mesa, name='actualizar_mesa'),

    # AJAX / JS
    path('mesa/guardar/', views.mesa_guardar, name='mesa_guardar'),
    path('mesa/eliminar/<int:mesa_id>/', views.eliminar_mesa_vista, name='eliminar_mesa_vista'),
]
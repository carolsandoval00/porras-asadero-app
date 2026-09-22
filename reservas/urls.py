from django.urls import path

from . import views

urlpatterns = [
    # Inicio
    path('', views.reserva_view, name='reserva_inicio'),

    # Reservas (HTML)
    path('crear/', views.crear_reserva, name='crear_reserva'),
    path('editar/<int:pk>/', views.editar_reserva, name='editar_reserva'),
    path('detalle/eliminar/', views.eliminar_detalle, name='eliminar_detalle'),

    # Mesas (HTML)
    path('mesas/diagrama/', views.diagrama_mesas, name='diagrama_mesas'),
    path('mesas/nueva/', views.gestion_mesas, name='gestion_mesas'),
    path('mesa/listar/', views.listar_mesas_vista, name='listar_mesas'),
    path('mesa/editar/<int:mesa_id>/', views.actualizar_mesa, name='actualizar_mesa'),
    path('mesa/eliminar/<int:mesa_id>/', views.eliminar_mesa_vista, name='eliminar_mesa_vista'),

    # API JSON que consume static/js/reservas.js
    path('api/reservas/', views.api_reservas, name='api_reservas'),
    path('api/reservas/guardar/', views.reserva_guardar, name='reserva_guardar'),
    path('api/reservas/eliminar/', views.reserva_eliminar, name='reserva_eliminar'),
    path('api/mesas/', views.api_mesas, name='api_mesas'),
    path('api/mesas/guardar/', views.mesa_guardar, name='mesa_guardar'),
    path('api/mesas/eliminar/', views.mesa_eliminar, name='mesa_eliminar'),
]
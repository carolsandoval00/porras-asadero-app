from django.urls import path
from . import views

urlpatterns = [
    # Vista principal
    path('', views.reserva_view, name='reserva_inicio'),

    # Rutas existentes
     path('mesa/listar/', views.listar_mesas_vista, name='listar_mesas'),
    path('mesa/editar/<int:mesa_id>/', views.actualizar_mesa,  name='actualizar_mesa'),
    path('detalle/eliminar/',          views.eliminar_detalle, name='eliminar_detalle'),

    # ── NUEVAS: reciben fetch() del JS del template ──────────
    path('mesa/guardar/',  views.mesa_guardar,  name='mesa_guardar'),
    path('mesa/eliminar/<int:mesa_id>/', views.eliminar_mesa_vista, name='eliminar_mesa_vista'),
]
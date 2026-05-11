from django.urls import path
from . import views

urlpatterns = [
    # Vista principal
    path('', views.reserva_view, name='reserva_inicio'),

    # Rutas existentes
    path('mesa/editar/',      views.actualizar_mesa,  name='actualizar_mesa'),
    path('detalle/eliminar/', views.eliminar_detalle, name='eliminar_detalle'),

    # ── NUEVAS: reciben fetch() del JS del template ──────────
    path('mesa/guardar/',  views.mesa_guardar,  name='mesa_guardar'),
    path('mesa/eliminar/', views.mesa_eliminar, name='mesa_eliminar'),
]
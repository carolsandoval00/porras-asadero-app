from django.contrib import admin

from .models import Mesa, Reserva


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero_mesa', 'capacidad', 'ubicacion', 'estado')
    list_filter = ('estado', 'ubicacion')
    search_fields = ('numero_mesa', 'ubicacion')


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_usuario', 'telefono', 'numero_mesa',
                    'fecha_reserva', 'hora_reserva', 'numero_personas', 'estado')
    list_filter = ('estado', 'fecha_reserva', 'numero_mesa')
    search_fields = ('nombre_cliente', 'telefono', 'email')
    date_hierarchy = 'fecha_reserva'
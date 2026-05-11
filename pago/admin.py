from django.contrib import admin
from .models import Pago, Caja

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['pk', 'orden', 'metodo_pago', 'monto', 'estado', 'fecha_pago']
    list_filter  = ['estado', 'metodo_pago']

@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ['pk', 'cajero', 'monto_inicial', 'estado', 'fecha_apertura']
    list_filter  = ['estado']
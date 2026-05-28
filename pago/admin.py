from django.contrib import admin
from .models import Pago, Caja

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['pk', 'pedido', 'metodo_pago', 'monto', 'fecha_pago']
    list_filter  = ['metodo_pago']

@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ['pk', 'cajero', 'monto_inicial', 'estado', 'fecha_apertura']
    list_filter  = ['estado']
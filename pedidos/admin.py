from django.contrib import admin
from .models import Pedido, Orden, Producto, Caja


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display  = ['pk', 'cliente', 'estado', 'total', 'fecha_creacion']
    list_filter   = ['estado']
    search_fields = ['cliente']


@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ['numero_orden', 'pedido', 'estado', 'total', 'creada_en']
    list_filter  = ['estado']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'categoria', 'precio', 'disponible', 'creado_en']
    list_filter   = ['categoria', 'disponible']
    search_fields = ['nombre']
    list_editable = ['precio', 'disponible']


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'responsable', 'saldo_inicial', 'estado', 'fecha_apertura']
    list_filter  = ['estado']
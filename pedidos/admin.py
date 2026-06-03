from django.contrib import admin
from .models import Pedido, Producto, Categoria


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display  = ['pk', 'cliente', 'estado', 'total', 'fecha_creacion']
    list_filter   = ['estado']
    search_fields = ['cliente__nombre_completo']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'categoria', 'precio', 'disponible', 'creado_en']
    list_filter   = ['categoria', 'disponible']
    search_fields = ['nombre']
    list_editable = ['precio', 'disponible']
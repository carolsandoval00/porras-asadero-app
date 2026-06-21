from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'pedidos'

urlpatterns = [
    # ── Dashboard ─────────────────────────────────────────────
    path('', views.dashboard, name='dashboard'),

    # ── Pedidos ───────────────────────────────────────────────
    path('pedidos/',                     views.pedido_lista,    name='pedido_lista'),
    path('pedidos/crear/',               views.pedido_crear,    name='pedido_crear'),
    path('pedidos/<int:pk>/editar/',     views.pedido_editar,   name='pedido_editar'),
    path('pedidos/<int:pk>/eliminar/',   views.pedido_eliminar, name='pedido_eliminar'),
    path('pedidos/exportar/pdf/',   views.pedido_exportar_pdf,   name='pedido_exportar_pdf'),
    path('pedidos/exportar/excel/', views.pedido_exportar_excel, name='pedido_exportar_excel'),

    # ── Órdenes ──────────────────────────────────────────────
    path('ordenes/',                    views.orden_lista,    name='orden_lista'),
    path('ordenes/crear/',              RedirectView.as_view(pattern_name='pedidos:pedido_crear', permanent=False), name='orden_crear'),
    path('ordenes/<int:pk>/',           views.orden_detalle,  name='orden_detalle'),
    path('ordenes/<int:pk>/editar/',    views.orden_editar,   name='orden_editar'),
    path('ordenes/<int:pk>/eliminar/',  views.orden_eliminar, name='orden_eliminar'),

    # ── Productos ─────────────────────────────────────────────
    path('productos/',                   views.producto_lista,    name='producto_lista'),
    path('productos/crear/',             views.producto_crear,    name='producto_crear'),
    path('productos/<int:pk>/editar/',   views.producto_editar,   name='producto_editar'),
    path('productos/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
    path('productos/exportar/pdf/',   views.producto_exportar_pdf,   name='producto_exportar_pdf'),
    path('productos/exportar/excel/', views.producto_exportar_excel, name='producto_exportar_excel'),

    # ── Categorías ────────────────────────────────────────────
    path('categorias/',                   views.categoria_lista,    name='categoria_lista'),
    path('categorias/crear/',             views.categoria_crear,    name='categoria_crear'),
    path('categorias/<int:pk>/editar/',   views.categoria_editar,   name='categoria_editar'),
    path('categorias/<int:pk>/eliminar/', views.categoria_eliminar, name='categoria_eliminar'),
    path('categorias/exportar/pdf/',   views.categoria_exportar_pdf,   name='categoria_exportar_pdf'),
    path('categorias/exportar/excel/', views.categoria_exportar_excel, name='categoria_exportar_excel'),

    # ── Clientes ──────────────────────────────────────────────
    path('clientes/',                   views.cliente_lista,    name='cliente_lista'),
    path('clientes/crear/',             views.cliente_crear,    name='cliente_crear'),
    path('clientes/<int:pk>/editar/',   views.cliente_editar,   name='cliente_editar'),
    path('clientes/<int:pk>/eliminar/', views.cliente_eliminar, name='cliente_eliminar'),
]
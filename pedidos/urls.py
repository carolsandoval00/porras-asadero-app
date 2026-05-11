from django.urls import path
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

    # ── Órdenes ──────────────────────────────────────────────
    path('ordenes/',                    views.orden_lista,    name='orden_lista'),
    path('ordenes/crear/',              views.orden_crear,    name='orden_crear'),
    path('ordenes/<int:pk>/',           views.orden_detalle,  name='orden_detalle'),
    path('ordenes/<int:pk>/editar/',    views.orden_editar,   name='orden_editar'),
    path('ordenes/<int:pk>/eliminar/',  views.orden_eliminar, name='orden_eliminar'),

    # ── Productos ─────────────────────────────────────────────
    path('productos/',                   views.producto_lista,    name='producto_lista'),
    path('productos/crear/',             views.producto_crear,    name='producto_crear'),
    path('productos/<int:pk>/editar/',   views.producto_editar,   name='producto_editar'),
    path('productos/<int:pk>/eliminar/', views.producto_eliminar, name='producto_eliminar'),
]
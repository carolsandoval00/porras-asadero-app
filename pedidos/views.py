from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from itertools import groupby
from .models import Pedido, Producto, PedidoItem, Categoria
from .forms import PedidoForm, ProductoForm, CategoriaForm, ClienteForm
from usuarios.models import Cliente
import json


# ── HELPERS PRIVADOS ────────────────────────────────────────────────

def _productos_disponibles():
    """
    Queryset centralizado de productos activos para los formularios de pedido.
    Evita repetir la misma query en múltiples puntos del mismo view.
    """
    return (
        Producto.objects
        .filter(disponible=True)
        .select_related('categoria')
        .order_by('categoria__nombre', 'nombre')
    )


def _parse_items_from_post(request):
    """
    Extrae los items del pedido enviados desde el frontend JS.
    Busca los productos por ID (no por nombre) para evitar colisiones.
    Retorna una lista de dicts {'producto': Producto, 'cantidad': int}.
    """
    items_data = []
    i = 0
    while True:
        producto_id = request.POST.get(f'items[{i}][id]')
        if producto_id is None:
            break
        try:
            producto = Producto.objects.get(pk=producto_id, disponible=True)
            cantidad = int(request.POST.get(f'items[{i}][cantidad]', 1))
            if cantidad > 0:
                items_data.append({'producto': producto, 'cantidad': cantidad})
        except (Producto.DoesNotExist, ValueError):
            pass
        i += 1
    return items_data


def _items_as_json(pedido):
    """
    Serialización auxiliar de items a formato JSON para precargar el formulario JS.
    """
    items = [
        {
            'id': str(item.producto.pk),
            'nombre': item.producto.nombre,
            'precio': int(item.precio_unitario),
            'cantidad': item.cantidad,
        }
        for item in pedido.items.select_related('producto').all()
    ]
    return json.dumps(items, ensure_ascii=False)


# ── TABLERO PRINCIPAL (DASHBOARD) ──────────────────────────────────

@login_required
def dashboard(request):
    """
    Tablero consolidado de estadísticas administrativas y últimos pedidos.
    """
    total_pedidos = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado='PREPARACION').count()
    total_productos = Producto.objects.count()
    total_categorias = Categoria.objects.count()
    total_clientes = Cliente.objects.count()
    ultimos_pedidos = (
        Pedido.objects
        .select_related('cliente', 'mesero', 'mesa')
        .order_by('-fecha_creacion')[:5]
    )

    return render(request, 'pedidos/dashboard.html', {
        'titulo': 'Módulo de Pedidos',
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'total_ordenes': total_pedidos,  # En el MER, Órdenes y Pedidos comparten la entidad Pedido
        'total_productos': total_productos,
        'total_categorias': total_categorias,
        'total_clientes': total_clientes,
        'ultimos_pedidos': ultimos_pedidos,
    })


# ── GESTIÓN DE PEDIDOS ───────────────────────────────────────────────

@login_required
def pedido_lista(request):
    """
    Listado interactivo de pedidos con filtros de búsqueda por mesa y estado.
    """
    q = request.GET.get('q', '').strip()
    estado_sel = request.GET.get('estado', '').strip()

    pedidos_qs = (
        Pedido.objects
        .select_related('cliente', 'mesero', 'mesa')
        .prefetch_related('items__producto')
        .order_by('-fecha_creacion')
    )

    if q:
        pedidos_qs = pedidos_qs.filter(
            Q(cliente__nombre_completo__icontains=q) | Q(descripcion__icontains=q)
        )
    if estado_sel:
        pedidos_qs = pedidos_qs.filter(estado=estado_sel)

    pedidos_lista = list(pedidos_qs)
    pedidos_por_fecha = []
    for fecha, grupo in groupby(pedidos_lista, key=lambda p: p.fecha_creacion.date()):
        items = list(grupo)
        pedidos_por_fecha.append({
            'fecha': fecha,
            'pedidos': items,
            'count': len(items),
        })

    return render(request, 'pedidos/pedido_lista.html', {
        'titulo': 'Módulo de Pedidos',
        'pedidos_por_fecha': pedidos_por_fecha,
        'estados': Pedido.ESTADO_CHOICES,
        'q': q,
        'estado_sel': estado_sel,
        'seccion_activa': 'pedido-lista',
    })


@login_required
def pedido_crear(request):
    """
    Formulario dinámico e interactivo de creación de un nuevo pedido.
    """
    # Calculamos una sola vez el catálogo disponible (se reutiliza en todos los renders)
    productos_disponibles = _productos_disponibles()

    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.mesero = request.user
            pedido.fecha_creacion = timezone.now()
            pedido.estado = 'PREPARACION'

            items_data = _parse_items_from_post(request)
            if not items_data:
                messages.error(request, '❌ Agrega al menos un producto al pedido.')
                return render(request, 'pedidos/pedido_form.html', {
                    'form': form,
                    'productos_disponibles': productos_disponibles,
                    'seccion_activa': 'pedido-crear',
                })

            total = sum(it['producto'].precio * it['cantidad'] for it in items_data)
            pedido.total = total
            pedido.subtotal = total
            pedido.impuestos = 0
            pedido.save()

            PedidoItem.objects.bulk_create([
                PedidoItem(
                    pedido=pedido,
                    producto=it['producto'],
                    cantidad=it['cantidad'],
                    precio_unitario=it['producto'].precio,
                )
                for it in items_data
            ])

            messages.success(request, f'✅ Pedido #{pedido.pk:02d} creado correctamente.')
            return redirect('pedidos:pedido_lista')

        messages.error(request, '❌ Corrige los errores en el formulario de pedido.')
        return render(request, 'pedidos/pedido_form.html', {
            'form': form,
            'productos_disponibles': productos_disponibles,
            'seccion_activa': 'pedido-crear',
        })

    form = PedidoForm()
    return render(request, 'pedidos/pedido_form.html', {
        'form': form,
        'productos_disponibles': productos_disponibles,
        'seccion_activa': 'pedido-crear',
    })


@login_required
def pedido_editar(request, pk):
    """
    Edición de un pedido y sus productos dinámicos con precarga JSON.
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    productos_disponibles = _productos_disponibles()

    if request.method == 'POST':
        items_data = _parse_items_from_post(request)
        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            p = form.save(commit=False)
            if items_data:
                total = sum(it['producto'].precio * it['cantidad'] for it in items_data)
                p.total = total
                p.subtotal = total
                p.save()
                pedido.items.all().delete()
                PedidoItem.objects.bulk_create([
                    PedidoItem(
                        pedido=pedido,
                        producto=it['producto'],
                        cantidad=it['cantidad'],
                        precio_unitario=it['producto'].precio,
                    )
                    for it in items_data
                ])
            else:
                p.save()
            messages.success(request, '✅ Pedido actualizado correctamente.')
            return redirect('pedidos:pedido_lista')

        return render(request, 'pedidos/pedido_form.html', {
            'form': form,
            'pedido': pedido,
            'pedido_items_json': _items_as_json(pedido),
            'productos_disponibles': productos_disponibles,
            'seccion_activa': 'pedido-editar',
        })

    form = PedidoForm(instance=pedido)
    return render(request, 'pedidos/pedido_form.html', {
        'form': form,
        'pedido': pedido,
        'pedido_items_json': _items_as_json(pedido),
        'productos_disponibles': productos_disponibles,
        'seccion_activa': 'pedido-editar',
    })


@login_required
def pedido_eliminar(request, pk):
    """
    Eliminación de un pedido específico.
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Pedido eliminado.')
    return redirect('pedidos:pedido_lista')


# ── GESTIÓN DE ÓRDENES (FACTURACIÓN) ──────────────────────────────────

@login_required
def orden_lista(request):
    """
    Listado financiero de órdenes comerciales agrupadas por fecha.
    """
    q_orden = request.GET.get('q_orden', '').strip()

    ordenes_qs = (
        Pedido.objects
        .select_related('cliente', 'mesero', 'mesa')
        .order_by('-fecha_creacion')
    )
    if q_orden:
        clean_q = q_orden.replace('ORD-', '').lstrip('0')
        if clean_q.isdigit():
            ordenes_qs = ordenes_qs.filter(
                Q(id=int(clean_q)) | Q(cliente__nombre_completo__icontains=q_orden)
            )
        else:
            ordenes_qs = ordenes_qs.filter(cliente__nombre_completo__icontains=q_orden)

    ordenes_lista = list(ordenes_qs)
    ordenes_por_fecha = []
    for fecha, grupo in groupby(ordenes_lista, key=lambda o: o.fecha_creacion.date()):
        items = list(grupo)
        ordenes_por_fecha.append({
            'fecha': fecha,
            'ordenes': items,
            'count': len(items),
        })

    return render(request, 'pedidos/orden_lista.html', {
        'titulo': 'Módulo de Pedidos',
        'ordenes_por_fecha': ordenes_por_fecha,
        'q_orden': q_orden,
        'seccion_activa': 'orden-lista',
    })


@login_required
def orden_detalle(request, pk):
    """
    Detalle de cobro/comprobante de una orden comercial.
    """
    orden = get_object_or_404(
        Pedido.objects.select_related('cliente', 'mesero', 'mesa').prefetch_related('pagos'),
        pk=pk,
    )
    return render(request, 'pedidos/orden_detalle.html', {
        'titulo': f'Orden {orden.numero_orden}',
        'orden': orden,
    })


@login_required
def orden_editar(request, pk):
    """
    Edición de estados e información de facturación de una orden.
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Pedido {pedido.numero_orden} actualizado.')
            return redirect('pedidos:orden_lista')
        return render(request, 'pedidos/orden_form.html', {
            'form_orden': form,
            'orden_editando': pedido,
            'seccion_activa': 'orden-editar',
        })

    form = PedidoForm(instance=pedido)
    return render(request, 'pedidos/orden_form.html', {
        'form_orden': form,
        'orden_editando': pedido,
        'seccion_activa': 'orden-editar',
    })


@login_required
def orden_eliminar(request, pk):
    """
    Eliminación de una orden comercial.
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Orden eliminada.')
    return redirect('pedidos:orden_lista')


# ── GESTIÓN DE PRODUCTOS ─────────────────────────────────────────────

@login_required
def producto_lista(request):
    """
    Listado y buscador de la carta de platos del asadero.
    """
    q_prod = request.GET.get('q_prod', '').strip()
    cat_sel = request.GET.get('categoria', '').strip()

    productos_qs = Producto.objects.select_related('categoria').all()
    if q_prod:
        productos_qs = productos_qs.filter(nombre__icontains=q_prod)
    if cat_sel:
        productos_qs = productos_qs.filter(categoria__id=cat_sel)

    return render(request, 'pedidos/producto_lista.html', {
        'titulo': 'Módulo de Pedidos',
        'productos': productos_qs,
        'categorias': Categoria.objects.all(),
        'q_prod': q_prod,
        'cat_sel': cat_sel,
        'seccion_activa': 'producto-lista',
    })


@login_required
def producto_crear(request):
    """
    Creación de nuevos platos/productos de la carta.
    """
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Producto creado correctamente.')
            return redirect('pedidos:producto_lista')
        messages.error(request, '❌ Corrige los errores en el formulario de producto.')
        return render(request, 'pedidos/producto_form.html', {
            'form_producto': form,
            'seccion_activa': 'producto-crear',
        })

    form = ProductoForm()
    return render(request, 'pedidos/producto_form.html', {
        'form_producto': form,
        'seccion_activa': 'producto-crear',
    })


@login_required
def producto_editar(request, pk):
    """
    Modificación de precios o detalles de un producto.
    """
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Producto actualizado correctamente.')
            return redirect('pedidos:producto_lista')
        return render(request, 'pedidos/producto_form.html', {
            'form_producto': form,
            'producto_editando': producto,
            'seccion_activa': 'producto-editar',
        })

    form = ProductoForm(instance=producto)
    return render(request, 'pedidos/producto_form.html', {
        'form_producto': form,
        'producto_editando': producto,
        'seccion_activa': 'producto-editar',
    })


@login_required
def producto_eliminar(request, pk):
    """
    Eliminación de un producto.
    """
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, '🗑️ Producto eliminado.')
    return redirect('pedidos:producto_lista')


# ── GESTIÓN DE CATEGORÍAS ──────────────────────────────────────────

@login_required
def categoria_lista(request):
    """
    Listado y filtrado de categorías de la carta.
    """
    q_cat = request.GET.get('q_cat', '').strip()

    categorias_qs = Categoria.objects.all()
    if q_cat:
        categorias_qs = categorias_qs.filter(nombre__icontains=q_cat)

    return render(request, 'pedidos/categoria_lista.html', {
        'titulo': 'Módulo de Pedidos',
        'categorias': categorias_qs,
        'q_cat': q_cat,
        'seccion_activa': 'categoria-lista',
    })


@login_required
def categoria_crear(request):
    """
    Creación de categorías del menú.
    """
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Categoría creada correctamente.')
            return redirect('pedidos:categoria_lista')
        messages.error(request, '❌ Corrige los errores en el formulario.')
        return render(request, 'pedidos/categoria_form.html', {
            'form_categoria': form,
            'seccion_activa': 'categoria-crear',
        })

    form = CategoriaForm()
    return render(request, 'pedidos/categoria_form.html', {
        'form_categoria': form,
        'seccion_activa': 'categoria-crear',
    })


@login_required
def categoria_editar(request, pk):
    """
    Modificación de nombres de categorías.
    """
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Categoría actualizada correctamente.')
            return redirect('pedidos:categoria_lista')
        return render(request, 'pedidos/categoria_form.html', {
            'form_categoria': form,
            'categoria_editando': categoria,
            'seccion_activa': 'categoria-editar',
        })

    form = CategoriaForm(instance=categoria)
    return render(request, 'pedidos/categoria_form.html', {
        'form_categoria': form,
        'categoria_editando': categoria,
        'seccion_activa': 'categoria-editar',
    })


@login_required
def categoria_eliminar(request, pk):
    """
    Eliminación de una categoría.
    """
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, '🗑️ Categoría eliminada.')
    return redirect('pedidos:categoria_lista')


# ── GESTIÓN DE CLIENTES ─────────────────────────────────────────────

@login_required
def cliente_lista(request):
    """
    Listado y buscador de clientes registrados en el restaurante.
    """
    q_cli = request.GET.get('q_cli', '').strip()

    clientes_qs = Cliente.objects.all()
    if q_cli:
        clientes_qs = clientes_qs.filter(
            Q(nombre_completo__icontains=q_cli) | Q(documento__icontains=q_cli)
        )

    return render(request, 'pedidos/cliente_lista.html', {
        'titulo': 'Módulo de Pedidos',
        'clientes': clientes_qs,
        'q_cli': q_cli,
        'seccion_activa': 'cliente-lista',
    })


@login_required
def cliente_crear(request):
    """
    Registro de nuevos clientes para reservas y compras.
    """
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cliente registrado correctamente.')
            return redirect('pedidos:cliente_lista')
        messages.error(request, '❌ Corrige los errores en el formulario.')
        return render(request, 'pedidos/cliente_form.html', {
            'form_cliente': form,
            'seccion_activa': 'cliente-crear',
        })

    form = ClienteForm()
    return render(request, 'pedidos/cliente_form.html', {
        'form_cliente': form,
        'seccion_activa': 'cliente-crear',
    })


@login_required
def cliente_editar(request, pk):
    """
    Edición de datos demográficos de un cliente.
    """
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cliente actualizado correctamente.')
            return redirect('pedidos:cliente_lista')
        return render(request, 'pedidos/cliente_form.html', {
            'form_cliente': form,
            'cliente_editando': cliente,
            'seccion_activa': 'cliente-editar',
        })

    form = ClienteForm(instance=cliente)
    return render(request, 'pedidos/cliente_form.html', {
        'form_cliente': form,
        'cliente_editando': cliente,
        'seccion_activa': 'cliente-editar',
    })


@login_required
def cliente_eliminar(request, pk):
    """
    Eliminación de un cliente.
    """
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, '🗑️ Cliente eliminado.')
    return redirect('pedidos:cliente_lista')
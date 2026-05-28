from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max
from django.utils import timezone
from itertools import groupby
from .models import Pedido, Producto, PedidoItem, Categoria
from .forms import PedidoForm, ProductoForm, CategoriaForm, ClienteForm
from usuarios.models import Cliente
from reservas.models import Mesa
import json


def _get_numero_orden():
    ultimo = Pedido.objects.aggregate(Max('id'))['id__max'] or 0
    return ultimo + 1


def _get_mesas_disponibles():
    # Obtener las mesas que no están ocupadas
    numeros_ocupados = []
    for mesa_id in Pedido.objects.filter(
        estado__in=['PREPARACION', 'SERVIDO']
    ).exclude(mesa=None).values_list('mesa_id', flat=True):
        numeros_ocupados.append(mesa_id)

    return Mesa.objects.exclude(
        numero_mesa__in=numeros_ocupados
    ).order_by('numero_mesa')


def _dashboard_context(request, extra=None):
    q                = request.GET.get('q', '').strip()
    estado_sel       = request.GET.get('estado', '').strip()
    q_prod           = request.GET.get('q_prod', '').strip()
    cat_sel          = request.GET.get('categoria', '').strip()
    q_orden          = request.GET.get('q_orden', '').strip()
    estado_orden_sel = request.GET.get('estado_orden', '').strip()
    seccion_get      = request.GET.get('seccion', '').strip()
    q_cat            = request.GET.get('q_cat', '').strip()
    q_cli            = request.GET.get('q_cli', '').strip()

    pedidos_qs = Pedido.objects.select_related('cliente', 'mesero', 'mesa').prefetch_related(
        'items__producto'
    ).order_by('fecha_creacion')
    
    if q:
        pedidos_qs = pedidos_qs.filter(Q(cliente__nombre_completo__icontains=q) | Q(descripcion__icontains=q))
    if estado_sel:
        pedidos_qs = pedidos_qs.filter(estado=estado_sel)

    productos_qs = Producto.objects.select_related('categoria').all()
    if q_prod:
        productos_qs = productos_qs.filter(nombre__icontains=q_prod)
    if cat_sel:
        productos_qs = productos_qs.filter(categoria__id=cat_sel)

    categorias_qs = Categoria.objects.all()
    if q_cat:
        categorias_qs = categorias_qs.filter(nombre__icontains=q_cat)

    clientes_qs = Cliente.objects.all()
    if q_cli:
        clientes_qs = clientes_qs.filter(Q(nombre_completo__icontains=q_cli) | Q(documento__icontains=q_cli))

    ordenes_qs = Pedido.objects.select_related('cliente', 'mesero', 'mesa').order_by('-fecha_creacion')
    if q_orden:
        # Permite buscar por cliente o por número de pedido (ej: ORD-00005 -> id=5)
        clean_q = q_orden.replace('ORD-', '').lstrip('0')
        if clean_q.isdigit():
            ordenes_qs = ordenes_qs.filter(Q(id=int(clean_q)) | Q(cliente__nombre_completo__icontains=q_orden))
        else:
            ordenes_qs = ordenes_qs.filter(cliente__nombre_completo__icontains=q_orden)
    if estado_orden_sel:
        ordenes_qs = ordenes_qs.filter(estado=estado_orden_sel)

    pedidos_lista = list(pedidos_qs)
    pedidos_por_fecha = []
    for fecha, grupo in groupby(pedidos_lista, key=lambda p: p.fecha_creacion.date()):
        items = list(grupo)
        pedidos_por_fecha.append({
            'fecha': fecha, 'pedidos': items,
            'total': sum(p.total for p in items), 'count': len(items),
        })

    ordenes_lista = list(ordenes_qs)
    ordenes_por_fecha = []
    for fecha, grupo in groupby(ordenes_lista, key=lambda o: o.fecha_creacion.date()):
        items = list(grupo)
        ordenes_por_fecha.append({
            'fecha': fecha, 'ordenes': items,
            'total': sum(o.total for o in items), 'count': len(items),
        })

    mesas_bd = _get_mesas_disponibles()

    ctx = {
        'titulo':             'Módulo de Pedidos',
        'nombre':             request.user.get_full_name() or request.user.username,
        'total_pedidos':      Pedido.objects.count(),
        'pedidos_pendientes': Pedido.objects.filter(estado='PREPARACION').count(),
        'total_ordenes':      Pedido.objects.count(),
        'total_productos':    Producto.objects.count(),
        'productos_activos':  Producto.objects.filter(disponible=True).count(),
        'total_categorias':   Categoria.objects.count(),
        'total_clientes':     Cliente.objects.count(),
        'ultimos_pedidos':    Pedido.objects.select_related('cliente', 'mesero').order_by('fecha_creacion')[:5],
        'pedidos':            pedidos_qs,
        'pedidos_por_fecha':  pedidos_por_fecha,
        'ordenes':            ordenes_qs,
        'ordenes_por_fecha':  ordenes_por_fecha,
        'productos':          productos_qs,
        'productos_disponibles': Producto.objects.filter(disponible=True).order_by('categoria__nombre', 'nombre'),
        'categorias':         categorias_qs,
        'clientes':           clientes_qs,
        'estados':            Pedido.ESTADO_CHOICES,
        'estados_orden':      Pedido.ESTADO_CHOICES,
        'q':                  q,
        'estado_sel':         estado_sel,
        'q_orden':            q_orden,
        'estado_orden_sel':   estado_orden_sel,
        'q_prod':             q_prod,
        'cat_sel':            cat_sel,
        'q_cat':              q_cat,
        'q_cli':              q_cli,
        'form_pedido':        PedidoForm(),
        'form_orden':         PedidoForm(), # Dummy para evitar errores
        'form_producto':      ProductoForm(),
        'form_categoria':     CategoriaForm(),
        'form_cliente':       ClienteForm(),
        'mesas_bd':           mesas_bd,
        'seccion_activa':     (extra.get('seccion_activa') if extra and 'seccion_activa' in extra else None) or seccion_get or None,
    }

    if extra:
        ctx.update(extra)

    return ctx


@login_required
def dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'pedido_crear':
            form = PedidoForm(request.POST)
            if form.is_valid():
                pedido = form.save(commit=False)
                pedido.mesero = request.user
                pedido.fecha_creacion = timezone.now()
                pedido.estado = 'PREPARACION'

                items_data = []
                i = 0
                while True:
                    nombre = request.POST.get(f'items[{i}][nombre]')
                    if nombre is None:
                        break
                    try:
                        producto = Producto.objects.get(nombre=nombre, disponible=True)
                        cantidad = int(request.POST.get(f'items[{i}][cantidad]', 1))
                        if cantidad > 0:
                            items_data.append({'producto': producto, 'cantidad': cantidad})
                    except Producto.DoesNotExist:
                        pass
                    i += 1

                if not items_data:
                    messages.error(request, '❌ Agrega al menos un producto al pedido.')
                    return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {
                        'form_pedido': form, 'seccion_activa': 'pedido-crear',
                    }))

                total = sum(it['producto'].precio * it['cantidad'] for it in items_data)
                pedido.total = total
                pedido.subtotal = total
                pedido.impuestos = 0
                pedido.save()

                for it in items_data:
                    PedidoItem.objects.create(
                        pedido=pedido, producto=it['producto'],
                        cantidad=it['cantidad'], precio_unitario=it['producto'].precio,
                    )

                messages.success(request, f'✅ Pedido #{pedido.pk:02d} creado correctamente.')
                return redirect('pedidos:dashboard')
            else:
                messages.error(request, '❌ Corrige los errores en el formulario de pedido.')
                return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {
                    'form_pedido': form, 'seccion_activa': 'pedido-crear',
                }))

        elif action == 'producto_crear':
            form = ProductoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, '✅ Producto creado correctamente.')
                return redirect('pedidos:dashboard')
            else:
                messages.error(request, '❌ Corrige los errores en el formulario de producto.')
                return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {
                    'form_producto': form, 'seccion_activa': 'producto-crear',
                }))

    return render(request, 'pedidos/dashboard.html', _dashboard_context(request))


@login_required
def pedido_lista(request):
    return redirect('pedidos:dashboard')


@login_required
def pedido_crear(request):
    form = PedidoForm(request.POST or None)
    if form.is_valid():
        pedido = form.save(commit=False)
        pedido.mesero = request.user
        pedido.fecha_creacion = timezone.now()
        pedido.estado = 'PREPARACION'
        pedido.save()
        messages.success(request, '✅ Pedido creado correctamente.')
        return redirect('pedidos:dashboard')
    return render(request, 'pedidos/pedido_form.html', {
        'titulo': 'Crear Pedido', 'nombre': request.user.username,
        'form': form, 'accion': 'Crear',
    })


@login_required
def pedido_editar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)

    if request.method == 'POST':
        items_data = []
        i = 0
        while True:
            nombre = request.POST.get(f'items[{i}][nombre]')
            if nombre is None:
                break
            try:
                producto = Producto.objects.get(nombre=nombre, disponible=True)
                cantidad = int(request.POST.get(f'items[{i}][cantidad]', 1))
                if cantidad > 0:
                    items_data.append({'producto': producto, 'cantidad': cantidad})
            except Producto.DoesNotExist:
                pass
            i += 1

        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            p = form.save(commit=False)
            if items_data:
                total = sum(it['producto'].precio * it['cantidad'] for it in items_data)
                p.total = total
                p.subtotal = total
                p.save()
                pedido.items.all().delete()
                for it in items_data:
                    PedidoItem.objects.create(
                        pedido=pedido, producto=it['producto'],
                        cantidad=it['cantidad'], precio_unitario=it['producto'].precio,
                    )
            else:
                p.save()
            messages.success(request, '✅ Pedido actualizado correctamente.')
            return redirect('pedidos:dashboard')

        ctx = _dashboard_context(request, {
            'form_pedido': form, 'pedido_editando': pedido,
            'pedido_items_json': _items_as_json(pedido), 'seccion_activa': 'pedido-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = PedidoForm(instance=pedido)
    ctx  = _dashboard_context(request, {
        'form_pedido': form, 'pedido_editando': pedido,
        'pedido_items_json': _items_as_json(pedido), 'seccion_activa': 'pedido-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)


def _items_as_json(pedido):
    items = [
        {'id': str(item.producto.pk), 'nombre': item.producto.nombre,
         'precio': int(item.precio_unitario), 'cantidad': item.cantidad}
        for item in pedido.items.select_related('producto').all()
    ]
    return json.dumps(items, ensure_ascii=False)


@login_required
def pedido_eliminar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Pedido eliminado.')
    return redirect('pedidos:dashboard')


@login_required
def orden_lista(request):
    qs = Pedido.objects.select_related('cliente', 'mesero').all()
    return render(request, 'pedidos/orden_lista.html', {
        'titulo': 'Órdenes', 'nombre': request.user.username, 'ordenes': qs,
    })


@login_required
def orden_crear(request):
    return redirect('pedidos:dashboard')


@login_required
def orden_detalle(request, pk):
    orden = get_object_or_404(
        Pedido.objects.select_related('cliente', 'mesero').prefetch_related('pagos'), pk=pk
    )
    return render(request, 'pedidos/orden_detalle.html', {
        'titulo': f'Orden {orden.numero_orden}', 'nombre': request.user.username, 'orden': orden,
    })


@login_required
def orden_editar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Pedido {pedido.numero_orden} actualizado.')
            return redirect('pedidos:dashboard')
        ctx = _dashboard_context(request, {
            'form_orden': form, 'orden_editando': pedido, 'seccion_activa': 'orden-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = PedidoForm(instance=pedido)
    ctx  = _dashboard_context(request, {
        'form_orden': form, 'orden_editando': pedido, 'seccion_activa': 'orden-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)


@login_required
def orden_eliminar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Orden eliminada.')
    return redirect('pedidos:dashboard')


@login_required
def producto_lista(request):
    return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {'seccion_activa': 'producto-lista'}))


@login_required
def producto_crear(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Producto creado correctamente.')
            return redirect('pedidos:producto_lista')
        else:
            messages.error(request, '❌ Corrige los errores en el formulario de producto.')
            return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {
                'form_producto': form, 'seccion_activa': 'producto-crear',
            }))
    
    form = ProductoForm()
    return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {
        'form_producto': form, 'seccion_activa': 'producto-crear',
    }))


@login_required
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Producto actualizado correctamente.')
            return redirect('pedidos:producto_lista')
        ctx = _dashboard_context(request, {
            'form_producto': form, 'producto_editando': producto, 'seccion_activa': 'producto-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = ProductoForm(instance=producto)
    ctx  = _dashboard_context(request, {
        'form_producto': form, 'producto_editando': producto, 'seccion_activa': 'producto-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)


@login_required
def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, '🗑️ Producto eliminado.')
    return redirect('pedidos:producto_lista')


# ─── CRUD de Categorías ───────────────────────────────────────

@login_required
def categoria_lista(request):
    return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {'seccion_activa': 'categoria-lista'}))


@login_required
def categoria_crear(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Categoría creada correctamente.')
            return redirect('pedidos:categoria_lista')
        else:
            messages.error(request, '❌ Corrige los errores en el formulario.')
            return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {
                'form_categoria': form, 'seccion_activa': 'categoria-crear',
            }))

    form = CategoriaForm()
    return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {
        'form_categoria': form, 'seccion_activa': 'categoria-crear',
    }))


@login_required
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Categoría actualizada correctamente.')
            return redirect('pedidos:categoria_lista')
        ctx = _dashboard_context(request, {
            'form_categoria': form, 'categoria_editando': categoria, 'seccion_activa': 'categoria-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = CategoriaForm(instance=categoria)
    ctx = _dashboard_context(request, {
        'form_categoria': form, 'categoria_editando': categoria, 'seccion_activa': 'categoria-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)


@login_required
def categoria_eliminar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, '🗑️ Categoría eliminada.')
    return redirect('pedidos:categoria_lista')


# ─── CRUD de Clientes ─────────────────────────────────────────

@login_required
def cliente_lista(request):
    return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {'seccion_activa': 'cliente-lista'}))


@login_required
def cliente_crear(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cliente registrado correctamente.')
            return redirect('pedidos:cliente_lista')
        else:
            messages.error(request, '❌ Corrige los errores en el formulario.')
            return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {
                'form_cliente': form, 'seccion_activa': 'cliente-crear',
            }))

    form = ClienteForm()
    return render(request, 'pedidos/dashboard.html', _dashboard_context(request, {
        'form_cliente': form, 'seccion_activa': 'cliente-crear',
    }))


@login_required
def cliente_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cliente actualizado correctamente.')
            return redirect('pedidos:cliente_lista')
        ctx = _dashboard_context(request, {
            'form_cliente': form, 'cliente_editando': cliente, 'seccion_activa': 'cliente-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = ClienteForm(instance=cliente)
    ctx = _dashboard_context(request, {
        'form_cliente': form, 'cliente_editando': cliente, 'seccion_activa': 'cliente-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)


@login_required
def cliente_eliminar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, '🗑️ Cliente eliminado.')
    return redirect('pedidos:cliente_lista')
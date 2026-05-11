from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from .models import Pedido, Orden, Producto, PedidoItem
from .forms import PedidoForm, OrdenForm, ProductoForm
import uuid
from itertools import groupby
from .models import Pedido, Orden, Producto, Caja, PedidoItem, Contador
from .forms import PedidoForm, OrdenForm, ProductoForm, CajaForm, CajaCierreForm
from reservas.models import Mesa

import json



# ─────────────────────────────────────────────────────────────
# HELPER — contexto completo para el dashboard
# ─────────────────────────────────────────────────────────────
def _dashboard_context(request, extra=None):
    q          = request.GET.get('q', '').strip()
    estado_sel = request.GET.get('estado', '').strip()
    q_prod     = request.GET.get('q_prod', '').strip()
    cat_sel    = request.GET.get('categoria', '').strip()
    q_orden          = request.GET.get('q_orden', '').strip()
    estado_orden_sel = request.GET.get('estado_orden', '').strip()
    seccion_get = request.GET.get('seccion', '').strip()

    pedidos_qs = Pedido.objects.select_related('creado_por').prefetch_related('items__producto', 'ordenes').order_by('-fecha_creacion')
    if q:
        pedidos_qs = pedidos_qs.filter(Q(cliente__icontains=q) | Q(descripcion__icontains=q))
    if estado_sel:
        pedidos_qs = pedidos_qs.filter(estado=estado_sel)

    productos_qs = Producto.objects.all()
    if q_prod:
        productos_qs = productos_qs.filter(nombre__icontains=q_prod)
    if cat_sel:
        productos_qs = productos_qs.filter(categoria=cat_sel)

    ordenes_qs = Orden.objects.select_related('pedido').order_by('-creada_en')
    if q_orden:
        ordenes_qs = ordenes_qs.filter(
            Q(pedido__cliente__icontains=q_orden) | Q(numero_orden__icontains=q_orden)
        )
    if estado_orden_sel:
        ordenes_qs = ordenes_qs.filter(estado=estado_orden_sel)

    # Agrupar pedidos por fecha
    pedidos_lista = list(pedidos_qs)
    pedidos_por_fecha = []
    for fecha, grupo in groupby(pedidos_lista, key=lambda p: p.fecha_creacion.date()):
        items = list(grupo)
        pedidos_por_fecha.append({
            'fecha':   fecha,
            'pedidos': items,
            'total':   sum(p.total for p in items),
            'count':   len(items),
        })

    # Agrupar órdenes por fecha
    ordenes_lista = list(ordenes_qs)
    ordenes_por_fecha = []
    for fecha, grupo in groupby(ordenes_lista, key=lambda o: o.creada_en.date()):
        items = list(grupo)
        ordenes_por_fecha.append({
            'fecha':   fecha,
            'ordenes': items,
            'total':   sum(o.total for o in items),
            'count':   len(items),
        })

    # ── CAMBIO 3: mesas desde la BD ordenadas por número ──────────────────────
    mesas_bd = Mesa.objects.all().order_by('numero_mesa')

    ctx = {
        'titulo': 'Módulo de Pedidos',
        'nombre': request.user.get_full_name() or request.user.username,
        'total_pedidos':      Pedido.objects.count(),
        'pedidos_pendientes': Pedido.objects.filter(estado='pendiente').count(),
        'total_ordenes':      Orden.objects.count(),
        'total_productos':    Producto.objects.count(),
        'productos_activos':  Producto.objects.filter(disponible=True).count(),
        'ultimos_pedidos':    Pedido.objects.select_related('creado_por').order_by('-fecha_creacion')[:5],
        'pedidos':   pedidos_qs,
        'ordenes':   ordenes_qs,
        'productos': productos_qs,
        'productos_disponibles': Producto.objects.filter(disponible=True).order_by('categoria', 'nombre'),
        'estados':         Pedido.ESTADO_CHOICES,
        'estados_orden':   Orden.ESTADO_CHOICES,
        'categorias':      Producto.CATEGORIA_CHOICES,
        'q':               q,
        'estado_sel':      estado_sel,
        'q_orden':         q_orden,
        'estado_orden_sel': estado_orden_sel,
        'q_prod':          q_prod,
        'cat_sel':         cat_sel,
        'form_pedido':   PedidoForm(),
        'form_orden':    OrdenForm(),
        'form_producto': ProductoForm(),
        'seccion_activa': (extra.get('seccion_activa') if extra and 'seccion_activa' in extra else None) or seccion_get or None,

        'pedidos':            pedidos_qs,
        'pedidos_por_fecha':  pedidos_por_fecha,
        'ordenes':            ordenes_qs,
        'ordenes_por_fecha':  ordenes_por_fecha,
        'productos':          productos_qs,
        'cajas':              Caja.objects.select_related('responsable').all(),
        'productos_disponibles': Producto.objects.filter(disponible=True).order_by('categoria', 'nombre'),
        'estados':            Pedido.ESTADO_CHOICES,
        'estados_orden':      Orden.ESTADO_CHOICES,
        'categorias':         Producto.CATEGORIA_CHOICES,
        'q':                  q,
        'estado_sel':         estado_sel,
        'q_orden':            q_orden,
        'estado_orden_sel':   estado_orden_sel,
        'q_prod':             q_prod,
        'cat_sel':            cat_sel,
        'form_pedido':        PedidoForm(),
        'form_orden':         OrdenForm(),
        'form_producto':      ProductoForm(),
        'form_caja':          CajaForm(),
        # ── CAMBIO 3: mesas disponibles para el selector ──────────────────────
        'mesas_bd':           mesas_bd,
        'seccion_activa':     (extra.get('seccion_activa') if extra and 'seccion_activa' in extra else None) or seccion_get or None,

    }

    if extra:
        ctx.update(extra)

    return ctx


# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────
def dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')

        # ── Crear Pedido ──────────────────────────────────────
        if action == 'pedido_crear':
            form = PedidoForm(request.POST)
            if form.is_valid():
                pedido = form.save(commit=False)
                pedido.creado_por = request.user



                # ── CAMBIO 2: fecha y hora del servidor ───────
                pedido.fecha_creacion = timezone.now()


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
                    ctx = _dashboard_context(request, {
                        'form_pedido': form,
                        'seccion_activa': 'pedido-crear',
                    })
                    return render(request, 'pedidos/dashboard.html', ctx)

                total = sum(it['producto'].precio * it['cantidad'] for it in items_data)
                pedido.total = total
                pedido.save()

                for it in items_data:
                    PedidoItem.objects.create(
                        pedido=pedido,
                        producto=it['producto'],
                        cantidad=it['cantidad'],
                        precio_unitario=it['producto'].precio,
                    )

                resumen_productos = ', '.join(
                    f"{it['cantidad']}x {it['producto'].nombre}" for it in items_data
                )



                # ── CAMBIO 1: numeración desde 01 ─────────────
                numero = Contador.siguiente()
                numero_str = f'{numero:02d}'


                Orden.objects.create(
                    pedido=pedido,
                    numero_orden=numero_str,
                    estado='abierta',
                    subtotal=total,
                    impuesto=0,
                    total=total,
                    notas=resumen_productos,
                )

                messages.success(request, f'✅ Pedido #{numero_str} creado correctamente.')
                return redirect('pedidos:dashboard')
            else:
                messages.error(request, '❌ Corrige los errores en el formulario de pedido.')
                ctx = _dashboard_context(request, {
                    'form_pedido': form,
                    'seccion_activa': 'pedido-crear',
                })
                return render(request, 'pedidos/dashboard.html', ctx)

        # ── Crear Producto ────────────────────────────────────
        elif action == 'producto_crear':
            form = ProductoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, '✅ Producto creado correctamente.')
                return redirect('pedidos:dashboard')
            else:
                messages.error(request, '❌ Corrige los errores en el formulario de producto.')
                ctx = _dashboard_context(request, {
                    'form_producto': form,
                    'seccion_activa': 'producto-crear',
                })
                return render(request, 'pedidos/dashboard.html', ctx)

    return render(request, 'pedidos/dashboard.html', _dashboard_context(request))


# ─────────────────────────────────────────────────────────────
# PEDIDOS
# ─────────────────────────────────────────────────────────────
def pedido_lista(request):
    return redirect('pedidos:dashboard')


def pedido_crear(request):
    form = PedidoForm(request.POST or None)
    if form.is_valid():
        pedido = form.save(commit=False)
        pedido.creado_por = request.user
        # ── CAMBIO 2 ──
        pedido.fecha_creacion = timezone.now()
        pedido.save()
        messages.success(request, '✅ Pedido creado correctamente.')
        return redirect('pedidos:dashboard')
    return render(request, 'pedidos/pedido_form.html', {
        'titulo': 'Crear Pedido',
        'nombre': request.user.username,
        'form':   form,
        'accion': 'Crear',
    })


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
                p.save()

                pedido.items.all().delete()
                for it in items_data:
                    PedidoItem.objects.create(
                        pedido=pedido,
                        producto=it['producto'],
                        cantidad=it['cantidad'],
                        precio_unitario=it['producto'].precio,
                    )

                resumen_productos = ', '.join(
                    f"{it['cantidad']}x {it['producto'].nombre}" for it in items_data
                )

                orden = pedido.ordenes.filter(estado='abierta').first()
                if orden:
                    orden.subtotal = total
                    orden.total    = total + orden.impuesto
                    orden.notas    = resumen_productos
                    orden.save()
            else:
                p.save()

            messages.success(request, '✅ Pedido actualizado correctamente.')
            return redirect('pedidos:dashboard')

        ctx = _dashboard_context(request, {
            'form_pedido':       form,
            'pedido_editando':   pedido,
            'pedido_items_json': _items_as_json(pedido),
            'seccion_activa':    'pedido-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = PedidoForm(instance=pedido)
    ctx  = _dashboard_context(request, {
        'form_pedido':       form,
        'pedido_editando':   pedido,
        'pedido_items_json': _items_as_json(pedido),
        'seccion_activa':    'pedido-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)


def _items_as_json(pedido):

    import json

    items = [
        {
            'id':       str(item.producto.pk),
            'nombre':   item.producto.nombre,
            'precio':   int(item.precio_unitario),
            'cantidad': item.cantidad,
        }
        for item in pedido.items.select_related('producto').all()
    ]
    return json.dumps(items, ensure_ascii=False)


def pedido_eliminar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Pedido eliminado.')
    return redirect('pedidos:dashboard')


# ─────────────────────────────────────────────────────────────
# ÓRDENES
# ─────────────────────────────────────────────────────────────
def orden_lista(request):
    qs = Orden.objects.select_related('pedido').all()
    return render(request, 'pedidos/orden_lista.html', {
        'titulo':  'Órdenes',
        'nombre':  request.user.username,
        'ordenes': qs,
    })


def orden_crear(request):
    form = OrdenForm(request.POST or None)
    if form.is_valid():
        orden = form.save(commit=False)
        # ── CAMBIO 1 ──
        numero = Contador.siguiente()
        orden.numero_orden = f'{numero:02d}'
        orden.save()
        messages.success(request, '✅ Orden creada.')
        return redirect('pedidos:dashboard')
    return render(request, 'pedidos/orden_form.html', {
        'titulo': 'Crear Orden',
        'nombre': request.user.username,
        'form':   form,
        'accion': 'Crear',
    })


def orden_detalle(request, pk):
    orden = get_object_or_404(
        Orden.objects.select_related('pedido').prefetch_related('pagos'), pk=pk
    )
    return render(request, 'pedidos/orden_detalle.html', {
        'titulo': f'Orden {orden.numero_orden}',
        'nombre': request.user.username,
        'orden':  orden,
    })


def orden_editar(request, pk):
    orden = get_object_or_404(Orden, pk=pk)

    if request.method == 'POST':
        form = OrdenForm(request.POST, instance=orden)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Orden {orden.numero_orden} actualizada.')
            return redirect('pedidos:dashboard')
        ctx = _dashboard_context(request, {
            'form_orden':     form,
            'orden_editando': orden,
            'seccion_activa': 'orden-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = OrdenForm(instance=orden)
    ctx  = _dashboard_context(request, {
        'form_orden':     form,
        'orden_editando': orden,
        'seccion_activa': 'orden-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)


def orden_eliminar(request, pk):
    orden = get_object_or_404(Orden, pk=pk)
    if request.method == 'POST':
        orden.delete()
        messages.success(request, '🗑️ Orden eliminada.')
    return redirect('pedidos:dashboard')


# ─────────────────────────────────────────────────────────────
# PRODUCTOS
# ─────────────────────────────────────────────────────────────
def producto_lista(request):
    q         = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    qs        = Producto.objects.all()
    if q:
        qs = qs.filter(nombre__icontains=q)
    if categoria:
        qs = qs.filter(categoria=categoria)
    return render(request, 'pedidos/producto_lista.html', {
        'titulo':     'Productos',
        'nombre':     request.user.username,
        'productos':  qs,
        'q':          q,
        'cat_sel':    categoria,
        'categorias': Producto.CATEGORIA_CHOICES,
    })


def producto_crear(request):
    form = ProductoForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Producto creado correctamente.')
        return redirect('pedidos:dashboard')
    return render(request, 'pedidos/producto_form.html', {
        'titulo': 'Crear Producto',
        'nombre': request.user.username,
        'form':   form,
        'accion': 'Crear',
    })


def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Producto actualizado correctamente.')
            return redirect('pedidos:dashboard')
        ctx = _dashboard_context(request, {
            'form_producto':     form,
            'producto_editando': producto,
            'seccion_activa':    'producto-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = ProductoForm(instance=producto)
    ctx  = _dashboard_context(request, {
        'form_producto':     form,
        'producto_editando': producto,
        'seccion_activa':    'producto-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)


def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, '🗑️ Producto eliminado.')
    return redirect('pedidos:dashboard')
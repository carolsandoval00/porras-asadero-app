from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Pedido, Orden, Producto, Caja
from .forms import PedidoForm, OrdenForm, ProductoForm, CajaForm, CajaCierreForm
import uuid


# ─────────────────────────────────────────────────────────────
# HELPER — contexto completo para el dashboard
# ─────────────────────────────────────────────────────────────
def _dashboard_context(request, extra=None):
    q          = request.GET.get('q', '').strip()
    estado_sel = request.GET.get('estado', '').strip()
    q_prod     = request.GET.get('q_prod', '').strip()
    cat_sel    = request.GET.get('categoria', '').strip()

    pedidos_qs = Pedido.objects.select_related('creado_por').order_by('-fecha_creacion')
    if q:
        pedidos_qs = pedidos_qs.filter(Q(cliente__icontains=q) | Q(descripcion__icontains=q))
    if estado_sel:
        pedidos_qs = pedidos_qs.filter(estado=estado_sel)

    productos_qs = Producto.objects.all()
    if q_prod:
        productos_qs = productos_qs.filter(nombre__icontains=q_prod)
    if cat_sel:
        productos_qs = productos_qs.filter(categoria=cat_sel)

    ctx = {
        'titulo': 'Módulo de Pedidos',
        'nombre': request.user.get_full_name() or request.user.username,

        # Stats
        'total_pedidos':      Pedido.objects.count(),
        'pedidos_pendientes': Pedido.objects.filter(estado='pendiente').count(),
        'total_ordenes':      Orden.objects.count(),
        'total_productos':    Producto.objects.count(),
        'productos_activos':  Producto.objects.filter(disponible=True).count(),
        'caja_abierta':       Caja.objects.filter(estado='abierta').first(),
        'ultimos_pedidos':    Pedido.objects.select_related('creado_por').order_by('-fecha_creacion')[:5],

        # Listas
        'pedidos':   pedidos_qs,
        'ordenes':   Orden.objects.select_related('pedido').all(),
        'productos': productos_qs,
        'cajas':     Caja.objects.select_related('responsable').all(),

        # Productos disponibles para el selector al crear pedidos
        'productos_disponibles': Producto.objects.filter(
            disponible=True
        ).order_by('categoria', 'nombre'),

        # Filtros
        'estados':    Pedido.ESTADO_CHOICES,
        'categorias': Producto.CATEGORIA_CHOICES,
        'q':          q,
        'estado_sel': estado_sel,
        'q_prod':     q_prod,
        'cat_sel':    cat_sel,

        # Formularios vacíos
        'form_pedido':   PedidoForm(),
        'form_orden':    OrdenForm(),
        'form_producto': ProductoForm(),
        'form_caja':     CajaForm(),
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

        if action == 'pedido_crear':
            form = PedidoForm(request.POST)
            if form.is_valid():
                pedido = form.save(commit=False)
                pedido.creado_por = request.user
                pedido.save()
                messages.success(request, '✅ Pedido creado correctamente.')
                return redirect('pedidos:dashboard')
            else:
                messages.error(request, '❌ Corrige los errores en el formulario de pedido.')

        elif action == 'orden_crear':
            form = OrdenForm(request.POST)
            if form.is_valid():
                orden = form.save(commit=False)
                orden.numero_orden = f'ORD-{uuid.uuid4().hex[:8].upper()}'
                orden.save()
                messages.success(request, '✅ Orden creada.')
                return redirect('pedidos:dashboard')
            else:
                messages.error(request, '❌ Corrige los errores en el formulario de orden.')

        elif action == 'producto_crear':
            form = ProductoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, '✅ Producto creado correctamente.')
                return redirect('pedidos:dashboard')
            else:
                messages.error(request, '❌ Corrige los errores en el formulario de producto.')

        elif action == 'caja_abrir':
            form = CajaForm(request.POST)
            if form.is_valid():
                caja = form.save(commit=False)
                caja.responsable    = request.user
                caja.fecha_apertura = timezone.now()
                caja.estado         = 'abierta'
                caja.save()
                messages.success(request, '✅ Caja abierta.')
                return redirect('pedidos:dashboard')
            else:
                messages.error(request, '❌ Corrige los errores en el formulario de caja.')

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
        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Pedido actualizado correctamente.')
            return redirect('pedidos:dashboard')
        ctx = _dashboard_context(request, {
            'form_pedido':     form,
            'pedido_editando': pedido,
            'seccion_activa':  'pedido-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = PedidoForm(instance=pedido)
    ctx  = _dashboard_context(request, {
        'form_pedido':     form,
        'pedido_editando': pedido,
        'seccion_activa':  'pedido-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)


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
        orden.numero_orden = f'ORD-{uuid.uuid4().hex[:8].upper()}'
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


# ─────────────────────────────────────────────────────────────
# CAJA
# ─────────────────────────────────────────────────────────────
def caja_lista(request):
    cajas = Caja.objects.select_related('responsable').all()
    return render(request, 'pedidos/caja_lista.html', {
        'titulo': 'Cajas',
        'nombre': request.user.username,
        'cajas':  cajas,
    })


def caja_abrir(request):
    form = CajaForm(request.POST or None)
    if form.is_valid():
        caja = form.save(commit=False)
        caja.responsable    = request.user
        caja.fecha_apertura = timezone.now()
        caja.estado         = 'abierta'
        caja.save()
        messages.success(request, '✅ Caja abierta.')
        return redirect('pedidos:caja_lista')
    return render(request, 'pedidos/caja_form.html', {
        'titulo': 'Abrir Caja',
        'nombre': request.user.username,
        'form':   form,
        'accion': 'Abrir',
    })


def caja_detalle(request, pk):
    caja = get_object_or_404(Caja.objects.select_related('responsable'), pk=pk)
    return render(request, 'pedidos/caja_detalle.html', {
        'titulo': f'Caja: {caja.nombre}',
        'nombre': request.user.username,
        'caja':   caja,
    })


def caja_actualizar(request, pk):
    caja = get_object_or_404(Caja, pk=pk)
    form = CajaForm(request.POST or None, instance=caja)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Caja actualizada.')
        return redirect('pedidos:caja_lista')
    return render(request, 'pedidos/caja_form.html', {
        'titulo': f'Actualizar Caja: {caja.nombre}',
        'nombre': request.user.username,
        'form':   form,
        'accion': 'Actualizar',
        'caja':   caja,
    })


def caja_cerrar(request, pk):
    caja = get_object_or_404(Caja, pk=pk, estado='abierta')
    form = CajaCierreForm(request.POST or None, instance=caja)
    if form.is_valid():
        c = form.save(commit=False)
        c.estado       = 'cerrada'
        c.fecha_cierre = timezone.now()
        c.save()
        messages.success(request, '🔒 Caja cerrada correctamente.')
        return redirect('pedidos:caja_lista')
    return render(request, 'pedidos/caja_cierre_form.html', {
        'titulo': f'Cerrar Caja: {caja.nombre}',
        'nombre': request.user.get_full_name() or request.user.username,
        'form':   form,
        'caja':   caja,
    })
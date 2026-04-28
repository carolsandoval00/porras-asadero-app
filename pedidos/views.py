from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Pedido, Orden, Producto, Caja
from .forms import PedidoForm, OrdenForm, ProductoForm, CajaForm, CajaCierreForm
from django.db.models import Sum, Q
from .models import Pedido, Orden, Pago, Caja
from .forms import PedidoForm, OrdenForm, PagoForm, CajaForm, CajaCierreForm
import uuid


# ─────────────────────────────────────────────────────────────
#  HELPER — contexto completo para el dashboard
#  Se usa tanto en dashboard() como en pedido_editar()
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

        # ── NUEVO: productos disponibles para el selector de pedidos ──
        # Cada vez que se cree o edite un producto con disponible=True,
        # aparecerá automáticamente en el menú al crear un pedido.
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

        # Formularios vacíos (se pueden sobreescribir con extra)
        'form_pedido':   PedidoForm(),
        'form_orden':    OrdenForm(),
        'form_producto': ProductoForm(),
        'form_caja':     CajaForm(),
    }

    if extra:
        ctx.update(extra)

    return ctx


# ─────────────────────────────────────────────────────────────
#  DASHBOARD
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

    # ── Filtros de búsqueda (GET) ──────────────────────────────
    q          = request.GET.get('q', '').strip()
    estado_sel = request.GET.get('estado', '').strip()

    pedidos_qs = Pedido.objects.select_related('creado_por').order_by('-fecha_creacion')
    if q:
        pedidos_qs = pedidos_qs.filter(
            Q(cliente__icontains=q) | Q(descripcion__icontains=q)
        )
    if estado_sel:
        pedidos_qs = pedidos_qs.filter(estado=estado_sel)
        
    q_orden          = request.GET.get('q_orden', '').strip()
    estado_orden_sel = request.GET.get('estado_orden', '').strip()

    ordenes_qs = Orden.objects.select_related('pedido').order_by('-creada_en')
    if q_orden:
        ordenes_qs = ordenes_qs.filter(
            Q(pedido__cliente__icontains=q_orden) | Q(numero_orden__icontains=q_orden)
        )
    if estado_orden_sel:
        ordenes_qs = ordenes_qs.filter(estado=estado_orden_sel)

    context = {
        'titulo': 'Módulo de Pedidos',
        'nombre': request.user.get_full_name() or request.user.username,

        # Stats del dashboard
        'total_pedidos':      Pedido.objects.count(),
        'pedidos_pendientes': Pedido.objects.filter(estado='pendiente').count(),
        'total_ordenes':      Orden.objects.count(),
        'ordenes_abiertas':   Orden.objects.filter(estado='abierta').count(),
        'total_pagos':        Pago.objects.filter(estado='aprobado').aggregate(t=Sum('monto'))['t'] or 0,
        'caja_abierta':       Caja.objects.filter(estado='abierta').first(),
        'ultimos_pedidos':    Pedido.objects.select_related('creado_por').order_by('-fecha_creacion')[:5],

        # Lista de pedidos filtrada
        'pedidos':    pedidos_qs,
        'ordenes':           ordenes_qs,
        'q_orden':           q_orden,
        'estado_orden_sel':  estado_orden_sel,
        'estados_orden':     Orden.ESTADO_CHOICES,
        'pagos':      Pago.objects.select_related('orden').all(),
        'cajas':      Caja.objects.select_related('responsable').all(),
        'estados':    Pedido.ESTADO_CHOICES,
        'q':          q,
        'estado_sel': estado_sel,

        # Formularios vacíos
        'form_pedido': PedidoForm(),
        'form_orden':  OrdenForm(),
        'form_pago':   PagoForm(),
        'form_caja':   CajaForm(),
    }
    return render(request, 'pedidos/dashboard.html', context)



# ─────────────────────────────────────────────────────────────
#  PEDIDOS
# ─────────────────────────────────────────────────────────────
def pedido_lista(request):
    """Redirige al dashboard — la lista está integrada allí."""
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
        'titulo': 'Crear Pedido', 'nombre': request.user.username,
        'form': form, 'accion': 'Crear',
    })
    """Redirige al dashboard — el formulario de creación está integrado allí."""
    return redirect('pedidos:dashboard')



def pedido_editar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)


    if request.method == 'POST':
        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Pedido actualizado correctamente.')
            return redirect('pedidos:dashboard')
        ctx = _dashboard_context(request, {
            'form_pedido':      form,
            'pedido_editando':  pedido,
            'seccion_activa':   'pedido-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = PedidoForm(instance=pedido)
    ctx  = _dashboard_context(request, {
        'form_pedido':     form,
        'pedido_editando': pedido,
        'seccion_activa':  'pedido-editar',
    })
    return render(request, 'pedidos/dashboard.html', ctx)

    form   = PedidoForm(request.POST or None, instance=pedido)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Pedido actualizado.')
        return redirect('pedidos:dashboard')
    # Si el form no es válido en POST, vuelve al dashboard con error
    if request.method == 'POST':
        messages.error(request, '❌ Corrige los errores al editar el pedido.')
        return redirect('pedidos:dashboard')
    # GET directo a esta URL — redirige al dashboard
    return redirect('pedidos:dashboard')



def pedido_eliminar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Pedido eliminado.')
    return redirect('pedidos:dashboard')


# ─────────────────────────────────────────────────────────────
#  ÓRDENES
# ─────────────────────────────────────────────────────────────
def orden_lista(request):
    """Redirige al dashboard — la lista está integrada allí."""
    return redirect('pedidos:dashboard')


def orden_crear(request):

    form = OrdenForm(request.POST or None)
    if form.is_valid():
        orden = form.save(commit=False)
        orden.numero_orden = f'ORD-{uuid.uuid4().hex[:8].upper()}'
        orden.save()
        messages.success(request, '✅ Orden creada.')
        return redirect('pedidos:dashboard')
    return render(request, 'pedidos/orden_form.html', {
        'titulo': 'Crear Orden', 'nombre': request.user.username,
        'form': form, 'accion': 'Crear',
    })

    """Redirige al dashboard — el formulario de creación está integrado allí."""
    return redirect('pedidos:dashboard')



def orden_detalle(request, pk):
    orden = get_object_or_404(
        Orden.objects.select_related('pedido').prefetch_related('pagos'), pk=pk
    )
    return render(request, 'pedidos/orden_detalle.html', {
        'titulo': f'Orden {orden.numero_orden}',
        'nombre': request.user.get_full_name() or request.user.username,
        'orden':  orden,
    })
    
def orden_editar(request, pk):
    orden = get_object_or_404(Orden, pk=pk)
    form  = OrdenForm(request.POST or None, instance=orden)
    if form.is_valid():
        form.save()
        messages.success(request, f'✅ Orden {orden.numero_orden} actualizada.')
        return redirect('pedidos:dashboard')
    return render(request, 'pedidos/orden_form.html', {
        'titulo': f'Editar Orden {orden.numero_orden}',
        'nombre': request.user.get_full_name() or request.user.username,
        'form':   form,
        'accion': 'Actualizar',
        'orden':  orden,
    })


def orden_eliminar(request, pk):
    orden = get_object_or_404(Orden, pk=pk)
    if request.method == 'POST':
        orden.delete()
        messages.success(request, '🗑️ Orden eliminada.')
    return redirect('pedidos:dashboard')


# ─────────────────────────────────────────────────────────────
#  PRODUCTOS
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
        'titulo': 'Productos', 'nombre': request.user.username,
        'productos': qs, 'q': q, 'cat_sel': categoria,
        'categorias': Producto.CATEGORIA_CHOICES,
    })


def producto_crear(request):
    form = ProductoForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Producto creado correctamente.')
        return redirect('pedidos:dashboard')
    return render(request, 'pedidos/producto_form.html', {
        'titulo': 'Crear Producto', 'nombre': request.user.username,
        'form': form, 'accion': 'Crear',
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
            'form_producto':      form,
            'producto_editando':  producto,
            'seccion_activa':     'producto-editar',
        })
        return render(request, 'pedidos/dashboard.html', ctx)

    form = ProductoForm(instance=producto)
    ctx  = _dashboard_context(request, {
        'form_producto':     form,
        'producto_editando': producto,
        'seccion_activa':    'producto-editar',

def pago_lista(request):
    """Redirige al dashboard — la lista está integrada allí."""
    return redirect('pedidos:dashboard')


def pago_crear(request):
    """Redirige al dashboard — el formulario de creación está integrado allí."""
    return redirect('pedidos:dashboard')


def pago_detalle(request, pk):
    pago = get_object_or_404(Pago.objects.select_related('orden'), pk=pk)
    return render(request, 'pedidos/pago_detalle.html', {
        'titulo': f'Pago #{pk}',
        'nombre': request.user.get_full_name() or request.user.username,
        'pago':   pago,

    })
    return render(request, 'pedidos/dashboard.html', ctx)



def producto_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, '🗑️ Producto eliminado.')

def pago_editar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    form = PagoForm(request.POST or None, instance=pago)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Pago actualizado.')
        return redirect('pedidos:dashboard')
    if request.method == 'POST':
        messages.error(request, '❌ Corrige los errores al editar el pago.')
        return redirect('pedidos:dashboard')

    return redirect('pedidos:dashboard')


# ─────────────────────────────────────────────────────────────
#  CAJA
# ─────────────────────────────────────────────────────────────
def caja_lista(request):
    """Redirige al dashboard — la lista está integrada allí."""
    return redirect('pedidos:dashboard')


def caja_abrir(request):
    """Redirige al dashboard — el formulario de apertura está integrado allí."""
    return redirect('pedidos:dashboard')


def caja_detalle(request, pk):
    caja = get_object_or_404(Caja.objects.select_related('responsable'), pk=pk)
    return render(request, 'pedidos/caja_detalle.html', {
        'titulo': f'Caja: {caja.nombre}',
        'nombre': request.user.get_full_name() or request.user.username,
        'caja':   caja,
    })


def caja_actualizar(request, pk):
    caja = get_object_or_404(Caja, pk=pk)
    form = CajaForm(request.POST or None, instance=caja)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Caja actualizada.')
        return redirect('pedidos:dashboard')
    if request.method == 'POST':
        messages.error(request, '❌ Corrige los errores al actualizar la caja.')
        return redirect('pedidos:dashboard')
    return redirect('pedidos:dashboard')


def caja_cerrar(request, pk):
    caja = get_object_or_404(Caja, pk=pk, estado='abierta')
    form = CajaCierreForm(request.POST or None, instance=caja)
    if form.is_valid():
        c = form.save(commit=False)
        c.estado       = 'cerrada'
        c.fecha_cierre = timezone.now()
        c.save()
        messages.success(request, '🔒 Caja cerrada correctamente.')
        return redirect('pedidos:dashboard')
    return render(request, 'pedidos/caja_cierre_form.html', {
        'titulo': f'Cerrar Caja: {caja.nombre}',
        'nombre': request.user.get_full_name() or request.user.username,
        'form':   form,
        'caja':   caja,
    })
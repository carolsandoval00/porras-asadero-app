from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from .models import Pedido, Orden, Pago, Caja
from .forms import PedidoForm, OrdenForm, PagoForm, CajaForm, CajaCierreForm
import uuid


# ─────────────────────────────────────────────────────────────
#  DASHBOARD — maneja todos los formularios del template
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

        elif action == 'pago_crear':
            form = PagoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, '✅ Pago registrado.')
                return redirect('pedidos:dashboard')
            else:
                messages.error(request, '❌ Corrige los errores en el formulario de pago.')

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
    q      = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    qs     = Pedido.objects.select_related('creado_por').all()
    if q:
        qs = qs.filter(Q(cliente__icontains=q) | Q(descripcion__icontains=q))
    if estado:
        qs = qs.filter(estado=estado)
    return render(request, 'pedidos/pedido_lista.html', {
        'titulo': 'Pedidos', 'nombre': request.user.username,
        'pedidos': qs, 'q': q, 'estado_sel': estado,
        'estados': Pedido.ESTADO_CHOICES,
    })


def pedido_crear(request):
    form = PedidoForm(request.POST or None)
    if form.is_valid():
        pedido = form.save(commit=False)
        pedido.creado_por = request.user
        pedido.save()
        messages.success(request, '✅ Pedido creado correctamente.')
        return redirect('pedidos:pedido_lista')
    return render(request, 'pedidos/pedido_form.html', {
        'titulo': 'Crear Pedido', 'nombre': request.user.username,
        'form': form, 'accion': 'Crear',
    })


def pedido_editar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    form   = PedidoForm(request.POST or None, instance=pedido)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Pedido actualizado.')
        return redirect('pedidos:pedido_lista')
    return render(request, 'pedidos/pedido_form.html', {
        'titulo': f'Editar Pedido #{pk}', 'nombre': request.user.username,
        'form': form, 'accion': 'Actualizar', 'pedido': pedido,
    })


def pedido_eliminar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Pedido eliminado.')
        return redirect('pedidos:dashboard')
    return redirect('pedidos:dashboard')


# ─────────────────────────────────────────────────────────────
#  ÓRDENES
# ─────────────────────────────────────────────────────────────
def orden_lista(request):
    qs = Orden.objects.select_related('pedido').all()
    return render(request, 'pedidos/orden_lista.html', {
        'titulo': 'Órdenes', 'nombre': request.user.username, 'ordenes': qs,
    })


def orden_crear(request):
    form = OrdenForm(request.POST or None)
    if form.is_valid():
        orden = form.save(commit=False)
        orden.numero_orden = f'ORD-{uuid.uuid4().hex[:8].upper()}'
        orden.save()
        messages.success(request, '✅ Orden creada.')
        return redirect('pedidos:orden_lista')
    return render(request, 'pedidos/orden_form.html', {
        'titulo': 'Crear Orden', 'nombre': request.user.username,
        'form': form, 'accion': 'Crear',
    })


def orden_detalle(request, pk):
    orden = get_object_or_404(Orden.objects.select_related('pedido').prefetch_related('pagos'), pk=pk)
    return render(request, 'pedidos/orden_detalle.html', {
        'titulo': f'Orden {orden.numero_orden}', 'nombre': request.user.username,
        'orden': orden,
    })
    
def orden_editar(request, pk):
    orden = get_object_or_404(Orden, pk=pk)
    form  = OrdenForm(request.POST or None, instance=orden)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Orden {orden.numero_orden} actualizada.')
        else:
            messages.error(request, '❌ Corrige los errores.')
    return redirect('pedidos:dashboard'
    )
    


def orden_eliminar(request, pk):
    orden = get_object_or_404(Orden, pk=pk)
    if request.method == 'POST':
        orden.delete()
        messages.success(request, '🗑️ Orden eliminada.')
        return redirect('pedidos:dashboard')
    return redirect('pedidos:dashboard')


# ─────────────────────────────────────────────────────────────
#  PAGOS
# ─────────────────────────────────────────────────────────────
def pago_lista(request):
    qs = Pago.objects.select_related('orden').all()
    return render(request, 'pedidos/pago_lista.html', {
        'titulo': 'Pagos', 'nombre': request.user.username, 'pagos': qs,
    })


def pago_crear(request):
    form = PagoForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Pago registrado.')
        return redirect('pedidos:pago_lista')
    return render(request, 'pedidos/pago_form.html', {
        'titulo': 'Crear Pago', 'nombre': request.user.username,
        'form': form, 'accion': 'Registrar',
    })


def pago_detalle(request, pk):
    pago = get_object_or_404(Pago.objects.select_related('orden'), pk=pk)
    return render(request, 'pedidos/pago_detalle.html', {
        'titulo': f'Pago #{pk}', 'nombre': request.user.username, 'pago': pago,
    })


def pago_editar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    form = PagoForm(request.POST or None, instance=pago)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Pago actualizado.')
        return redirect('pedidos:pago_lista')
    return render(request, 'pedidos/pago_form.html', {
        'titulo': f'Editar Pago #{pk}', 'nombre': request.user.username,
        'form': form, 'accion': 'Actualizar', 'pago': pago,
    })


# ─────────────────────────────────────────────────────────────
#  CAJA
# ─────────────────────────────────────────────────────────────
def caja_lista(request):
    cajas = Caja.objects.select_related('responsable').all()
    return render(request, 'pedidos/caja_lista.html', {
        'titulo': 'Cajas', 'nombre': request.user.username, 'cajas': cajas,
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
        'titulo': 'Abrir Caja', 'nombre': request.user.username,
        'form': form, 'accion': 'Abrir',
    })


def caja_detalle(request, pk):
    caja = get_object_or_404(Caja.objects.select_related('responsable'), pk=pk)
    return render(request, 'pedidos/caja_detalle.html', {
        'titulo': f'Caja: {caja.nombre}', 'nombre': request.user.username, 'caja': caja,
    })


def caja_actualizar(request, pk):
    caja = get_object_or_404(Caja, pk=pk)
    form = CajaForm(request.POST or None, instance=caja)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Caja actualizada.')
        return redirect('pedidos:caja_lista')
    return render(request, 'pedidos/caja_form.html', {
        'titulo': f'Actualizar Caja: {caja.nombre}', 'nombre': request.user.username,
        'form': form, 'accion': 'Actualizar', 'caja': caja,
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
        'titulo': f'Cerrar Caja: {caja.nombre}', 'nombre': request.user.username,
        'form': form, 'caja': caja,
    })
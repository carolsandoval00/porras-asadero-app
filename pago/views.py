from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum
from itertools import groupby
from .models import Pago, AperturaCaja
from .forms import PagoForm, AperturaCajaForm
from pedidos.models import Orden


def pago_dashboard(request):
    form_apertura = AperturaCajaForm()
    form = PagoForm()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'abrir_caja':
            form_apertura = AperturaCajaForm(request.POST)
            if form_apertura.is_valid():
                apertura = form_apertura.save(commit=False)
                apertura.estado = 'abierta'
                apertura.save()
                messages.success(request, '✅ Caja abierta correctamente.')
                return redirect('pago:dashboard')
        else:
            post_data = request.POST.copy()
            orden_id  = post_data.get('orden')
            if orden_id:
                try:
                    orden = Orden.objects.get(pk=orden_id)
                    post_data['monto'] = orden.total
                except Orden.DoesNotExist:
                    pass
            form = PagoForm(post_data)
            if form.is_valid():
                form.save()
                messages.success(request, '✅ Pago registrado correctamente.')
                return redirect('pago:dashboard')

    ordenes_sin_pago = Orden.objects.exclude(
        pagos__estado='aprobado'
    ).select_related('pedido').order_by('-creada_en')

    pagos_qs = Pago.objects.select_related('orden__pedido').order_by('-fecha_pago')

    pagos_por_fecha = []
    for fecha, grupo in groupby(pagos_qs, key=lambda p: p.fecha_pago.date()):
        items = list(grupo)
        pagos_por_fecha.append({
            'fecha': fecha,
            'pagos': items,
            'total': sum(p.monto for p in items),
            'count': len(items),
        })

    context = {
        'form':             form,
        'form_apertura':    form_apertura,
        'pagos_por_fecha':  pagos_por_fecha,
        'ordenes_sin_pago': ordenes_sin_pago,
        'total_pagos':      pagos_qs.count(),
        'pagos_aprobados':  pagos_qs.filter(estado='aprobado').count(),
        'pagos_pendientes': pagos_qs.filter(estado='pendiente').count(),
        'monto_total':      pagos_qs.filter(estado='aprobado').aggregate(
                                t=Sum('monto'))['t'] or 0,
        'nombre':           request.user.get_full_name() or request.user.username,
        'cajas':            AperturaCaja.objects.all().order_by('-fecha_apertura'),
        'tab_activo':       'consultar-caja',
    }
    return render(request, 'pago/dashboard.html', context)


def pago_editar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    form = PagoForm(request.POST or None, instance=pago)
    if form.is_valid():
        form.save()
        messages.success(request, ' Pago actualizado.')
        return redirect('pago:dashboard')
    return render(request, 'pago/form.html', {
        'form':   form,
        'pago':   pago,
        'nombre': request.user.get_full_name() or request.user.username,
    })


def pago_eliminar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    if request.method == 'POST':
        pago.delete()
        messages.success(request, '🗑️ Pago eliminado.')
    return redirect('pago:dashboard')


def caja_detalle(request, pk):
    caja_seleccionada = get_object_or_404(AperturaCaja, pk=pk)

    pagos_caja = Pago.objects.filter(
        fecha_pago__gte=caja_seleccionada.fecha_apertura
    ).select_related('orden__pedido').order_by('-fecha_pago')

    total_ingresos   = pagos_caja.filter(estado='aprobado').aggregate(t=Sum('monto'))['t'] or 0
    total_pendientes = pagos_caja.filter(estado='pendiente').aggregate(t=Sum('monto'))['t'] or 0

    # Reutilizamos todo el contexto del dashboard
    form_apertura = AperturaCajaForm()
    form = PagoForm()

    ordenes_sin_pago = Orden.objects.exclude(
        pagos__estado='aprobado'
    ).select_related('pedido').order_by('-creada_en')

    pagos_qs = Pago.objects.select_related('orden__pedido').order_by('-fecha_pago')

    pagos_por_fecha = []
    for fecha, grupo in groupby(pagos_qs, key=lambda p: p.fecha_pago.date()):
        items = list(grupo)
        pagos_por_fecha.append({
            'fecha': fecha,
            'pagos': items,
            'total': sum(p.monto for p in items),
            'count': len(items),
        })

    context = {
        'form':               form,
        'form_apertura':      form_apertura,
        'pagos_por_fecha':    pagos_por_fecha,
        'ordenes_sin_pago':   ordenes_sin_pago,
        'total_pagos':        pagos_qs.count(),
        'pagos_aprobados':    pagos_qs.filter(estado='aprobado').count(),
        'pagos_pendientes':   pagos_qs.filter(estado='pendiente').count(),
        'monto_total':        pagos_qs.filter(estado='aprobado').aggregate(
                                  t=Sum('monto'))['t'] or 0,
        'nombre':             request.user.get_full_name() or request.user.username,
        'cajas':              AperturaCaja.objects.all().order_by('-fecha_apertura'),
        # datos del detalle
        'caja_seleccionada':  caja_seleccionada,
        'pagos_caja':         pagos_caja,
        'total_ingresos':     total_ingresos,
        'total_pendientes':   total_pendientes,
        'saldo_final':        caja_seleccionada.monto_inicial + total_ingresos,
        'tab_activo':         'detalle-caja',
    }
    return render(request, 'pago/dashboard.html', context)
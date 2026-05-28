from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse
from itertools import groupby
from .models import Pago, Caja
from .forms import PagoForm, CajaForm
from pedidos.models import Pedido


@login_required
def pago_dashboard(request):
    form_apertura = CajaForm()
    form = PagoForm()

    caja_activa = Caja.objects.filter(estado='ABIERTA').first()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'abrir_caja':
            form_apertura = CajaForm(request.POST)
            if form_apertura.is_valid():
                apertura = form_apertura.save(commit=False)
                apertura.estado = 'ABIERTA'
                apertura.save()
                messages.success(request, '✅ Caja abierta correctamente.')
                return redirect('pago:dashboard')
            else:
                messages.error(request, '❌ Revisa los campos e intenta de nuevo.')

        elif action == 'cerrar_caja':
            caja_id = request.POST.get('caja_id')
            try:
                caja = Caja.objects.get(pk=caja_id, estado='ABIERTA')
                caja.estado = 'CERRADA'
                caja.fecha_cierre = timezone.now()
                caja.save()
                messages.success(request, '🔒 Caja cerrada correctamente.')
            except Caja.DoesNotExist:
                messages.error(request, '❌ No se encontró la caja o ya está cerrada.')
            return redirect('pago:dashboard')

        elif action == 'editar_caja':
            caja_id      = request.POST.get('caja_id')
            cajero_id    = request.POST.get('cajero')
            observaciones = request.POST.get('observaciones', '').strip()

            try:
                caja = Caja.objects.get(pk=caja_id)
                if cajero_id:
                    caja.cajero_id = cajero_id
                caja.observaciones = observaciones
                caja.save()
                return JsonResponse({
                    'ok': True,
                    'cajero': caja.cajero.username,
                    'observaciones': caja.observaciones or '—',
                })
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=400)

        else:
            post_data = request.POST.copy()
            pedido_id  = post_data.get('pedido')
            if pedido_id:
                try:
                    pedido = Pedido.objects.get(pk=pedido_id)
                    post_data['monto'] = pedido.total
                except Pedido.DoesNotExist:
                    pass
            form = PagoForm(post_data)
            if form.is_valid():
                pago = form.save(commit=False)
                if caja_activa:
                    pago.caja = caja_activa
                    pago.save()
                    # Actualizar estado de comanda
                    pago.pedido.estado = 'PAGADO'
                    pago.pedido.save()
                    messages.success(request, '✅ Pago registrado y comanda marcada como PAGADA.')
                else:
                    messages.error(request, '❌ No puedes registrar pagos sin una caja abierta.')
                return redirect('pago:dashboard')

    # Pedidos pendientes de pago
    ordenes_sin_pago = Pedido.objects.exclude(
        estado='PAGADO'
    ).order_by('-fecha_creacion')

    pagos_qs = Pago.objects.select_related('pedido').order_by('-fecha_pago')

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
        'pagos_aprobados':  pagos_qs.count(),
        'pagos_pendientes': 0,
        'monto_total':      pagos_qs.aggregate(t=Sum('monto'))['t'] or 0,
        'nombre':           request.user.get_full_name() or request.user.username,
        'cajas':            Caja.objects.select_related('cajero').all().order_by('-fecha_apertura'),
        'tab_activo':       'pendientes',
        'caja_activa':      caja_activa,
    }
    return render(request, 'pago/dashboard.html', context)


@login_required
def pago_editar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    form = PagoForm(request.POST or None, instance=pago)
    if form.is_valid():
        form.save()
        messages.success(request, '✅ Pago actualizado.')
        return redirect('pago:dashboard')
    return render(request, 'pago/form.html', {
        'form':   form,
        'pago':   pago,
        'nombre': request.user.get_full_name() or request.user.username,
    })


@login_required
def pago_eliminar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    if request.method == 'POST':
        pago.delete()
        messages.success(request, '🗑️ Pago eliminado.')
    return redirect('pago:dashboard')


@login_required
def caja_detalle(request, pk):
    caja_seleccionada = get_object_or_404(Caja, pk=pk)
    pagos_caja = Pago.objects.filter(caja=caja_seleccionada).select_related('pedido').order_by('-fecha_pago')

    total_ingresos = pagos_caja.aggregate(t=Sum('monto'))['t'] or 0
    total_pendientes = 0

    form_apertura = CajaForm()
    form = PagoForm()

    ordenes_sin_pago = Pedido.objects.exclude(
        estado='PAGADO'
    ).order_by('-fecha_creacion')

    pagos_qs = Pago.objects.select_related('pedido').order_by('-fecha_pago')

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
        'pagos_aprobados':    pagos_qs.count(),
        'pagos_pendientes':   0,
        'monto_total':        pagos_qs.aggregate(t=Sum('monto'))['t'] or 0,
        'nombre':             request.user.get_full_name() or request.user.username,
        'cajas':              Caja.objects.select_related('cajero').all().order_by('-fecha_apertura'),
        'caja_seleccionada':  caja_seleccionada,
        'pagos_caja':         pagos_caja,
        'total_ingresos':     total_ingresos,
        'total_pendientes':   total_pendientes,
        'saldo_final':        caja_seleccionada.monto_inicial + total_ingresos,
        'tab_activo':         'detalle-caja',
        'caja_activa':        Caja.objects.filter(estado='ABIERTA').first(),
    }
    return render(request, 'pago/dashboard.html', context)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from itertools import groupby
from .models import Pago
from .forms import PagoForm
from pedidos.models import Orden


def pago_dashboard(request):
    if request.method == 'POST':
        form = PagoForm(request.POST)
        if form.is_valid():
            pago = form.save(commit=False)
            if pago.orden:
                pago.monto = pago.orden.total
            pago.save()
            messages.success(request, ' Pago registrado correctamente.')
            return redirect('pago:dashboard')
    else:
        form = PagoForm()

    ordenes_sin_pago = Orden.objects.exclude(
        pagos__estado='aprobado'
    ).select_related('pedido').order_by('-creada_en')

    pagos_qs = Pago.objects.select_related('orden__pedido').order_by('-fecha_pago')

    # Agrupar pagos por fecha
    pagos_por_fecha = []
    for fecha, grupo in groupby(pagos_qs, key=lambda p: p.fecha_pago.date()):
        items = list(grupo)
        pagos_por_fecha.append({
            'fecha':  fecha,
            'pagos':  items,
            'total':  sum(p.monto for p in items),
            'count':  len(items),
        })

    context = {
        'form':             form,
        'pagos_por_fecha':  pagos_por_fecha,
        'ordenes_sin_pago': ordenes_sin_pago,
        'total_pagos':      pagos_qs.count(),
        'pagos_aprobados':  pagos_qs.filter(estado='aprobado').count(),
        'pagos_pendientes': pagos_qs.filter(estado='pendiente').count(),
        'monto_total':      pagos_qs.filter(estado='aprobado').aggregate(
                                t=Sum('monto'))['t'] or 0,
        'nombre':           request.user.get_full_name() or request.user.username,
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
        messages.success(request, ' Pago eliminado.')
        return redirect('pago:dashboard')
    return redirect('pago:dashboard')
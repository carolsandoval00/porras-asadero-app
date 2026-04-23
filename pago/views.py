from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum
from .models import Pago
from .forms import PagoForm

def pago_dashboard(request):
    form = PagoForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Pago registrado correctamente.')
            return redirect('pago:dashboard')

    pagos = Pago.objects.all()
    context = {
        'pagos':            pagos,
        'form':             form,
        'total_pagos':      pagos.count(),
        'pagos_aprobados':  pagos.filter(estado='aprobado').count(),
        'pagos_pendientes': pagos.filter(estado='pendiente').count(),
        'monto_total':      pagos.filter(estado='aprobado').aggregate(t=Sum('monto'))['t'] or 0,
        'nombre':           request.user.get_full_name() or request.user.username,
    }
    return render(request, 'pago/dashboard.html', context)

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

def pago_eliminar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    if request.method == 'POST':
        pago.delete()
        messages.success(request, '🗑️ Pago eliminado.')
        return redirect('pago:dashboard')
    return render(request, 'pago/confirmar_eliminar.html', {
        'pago':   pago,
        'nombre': request.user.get_full_name() or request.user.username,
    })
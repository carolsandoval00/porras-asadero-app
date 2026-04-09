from django.shortcuts import render, get_object_or_404, redirect
from .models import DetalleReserva
from django.contrib import messages

def eliminar_detalle(request):
    detalles = DetalleReserva.objects.all()

    if request.method == 'POST':
        detalle_id = request.POST.get('detalle')

        if detalle_id:
            detalle = get_object_or_404(DetalleReserva, pk=detalle_id)
            detalle.delete()
            messages.success(request, f'Detalle #{detalle_id} eliminado correctamente.')
            return redirect('eliminar_detalle')
        else:
            messages.error(request, 'Debes seleccionar un detalle para eliminar.')

    return render(request, 'reservas/eliminar_detalle.html', {
        'detalles': detalles
    })
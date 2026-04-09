from django.shortcuts import render, get_object_or_404, redirect
from .models import DetalleReserva, Mesa
from django.contrib import messages

# -------------------------
# ELIMINAR DETALLE RESERVA
# -------------------------
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


# -------------------------
# ACTUALIZAR MESA
# -------------------------
def actualizar_mesa(request):

    try:
        mesa = Mesa.objects.all()[0]
    except IndexError:
        return render(request, 'reservas/sin_mesas.html')

    if request.method == 'POST':
        mesa.capacidad = request.POST.get('capacidad')
        mesa.ubicacion = request.POST.get('ubicacion')
        mesa.estado = request.POST.get('estado')
        mesa.save()

    return render(request, 'reservas/actualizar_mesa.html', {
        'mesa': mesa
    })
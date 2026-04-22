from django.shortcuts import render, get_object_or_404, redirect
from .models import DetalleReserva, Mesa
from django.contrib import messages

# -------------------------
# VISTA PRINCIPAL (CORREGIDA)
# -------------------------
def reserva_view(request):
    """Renderiza el panel principal de reservas"""
    # CORRECCIÓN: Se ajustó el nombre al archivo exacto de tu carpeta templates
    return render(request, 'reserva_inicio.html')

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

    # NOTA: Asegúrate de que este archivo también esté en la raíz de templates 
    # o ajusta la ruta si está dentro de una carpeta.
    return render(request, 'reservas/eliminar_detalle.html', {
        'detalles': detalles
    })


# -------------------------
# ACTUALIZAR MESA
# -------------------------
def actualizar_mesa(request):
    # Intentamos obtener la primera mesa disponible
    mesa = Mesa.objects.first()
    
    if not mesa:
        # Asegúrate de que este archivo exista en la ruta especificada
        return render(request, 'reservas/sin_mesas.html')

    if request.method == 'POST':
        mesa.capacidad = request.POST.get('capacidad')
        mesa.ubicacion = request.POST.get('ubicacion')
        mesa.estado = request.POST.get('estado')
        mesa.save()
        messages.success(request, 'Mesa actualizada correctamente.')
        return redirect('actualizar_mesa')

    return render(request, 'reservas/actualizar_mesa.html', {
        'mesa': mesa
    })
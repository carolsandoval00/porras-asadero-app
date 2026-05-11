from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import DetalleReserva, Mesa
import json


# ─────────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────────────────────
def reserva_view(request):
    """Renderiza el panel principal de reservas"""
    return render(request, 'reserva_inicio.html')


# ─────────────────────────────────────────────────────────────
# GUARDAR / ACTUALIZAR MESA DESDE EL JS
# Recibe fetch() desde el template cuando se crea o edita una mesa
# ─────────────────────────────────────────────────────────────
@require_POST
def mesa_guardar(request):
    try:
        data = json.loads(request.body)
        Mesa.objects.update_or_create(
            numero_mesa=data['numero_mesa'],
            defaults={
                'capacidad': data['capacidad'],
                'ubicacion': data['ubicacion'],
                'estado':    data['estado'],
            }
        )
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


# ─────────────────────────────────────────────────────────────
# ELIMINAR MESA DESDE EL JS
# ─────────────────────────────────────────────────────────────
@require_POST
def mesa_eliminar(request):
    try:
        data = json.loads(request.body)
        Mesa.objects.filter(numero_mesa=data['numero_mesa']).delete()
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


# ─────────────────────────────────────────────────────────────
# ELIMINAR DETALLE RESERVA
# ─────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────
# ACTUALIZAR MESA (vista HTML existente)
# ─────────────────────────────────────────────────────────────
def actualizar_mesa(request):
    mesa = Mesa.objects.first()

    if not mesa:
        return render(request, 'reservas/sin_mesas.html')

    if request.method == 'POST':
        mesa.capacidad = request.POST.get('capacidad')
        mesa.ubicacion = request.POST.get('ubicacion')
        mesa.estado    = request.POST.get('estado')
        mesa.save()
        messages.success(request, 'Mesa actualizada correctamente.')
        return redirect('actualizar_mesa')

    return render(request, 'reservas/actualizar_mesa.html', {
        'mesa': mesa
    })
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Mesa
from .models import Reserva, Mesa
import json


# ─────────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────────────────────
@login_required
def reserva_view(request):

    """Renderiza el panel principal de reservas"""
    rol = getattr(request.user, 'rol', None)
    if rol in ('CAJERO', 'CAJA', 'COCINA') and not request.user.is_superuser:
        return render(request, 'usuarios/login.html', {'vista': 'sin_permisos'})
        return render(request, 'reserva_inicio.html')


# ─────────────────────────────────────────────────────────────
# GUARDAR / ACTUALIZAR MESA DESDE EL JS
# ─────────────────────────────────────────────────────────────
@require_POST
@login_required
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
@login_required
def eliminar_mesa_vista(request, mesa_id):
    mesa = get_object_or_404(Mesa, numero_mesa=mesa_id)
    mesa.delete()
    messages.success(request, f'Mesa {mesa_id} eliminada correctamente.')
    return redirect('listar_mesas')


# ─────────────────────────────────────────────────────────────
# ELIMINAR DETALLE RESERVA
# ─────────────────────────────────────────────────────────────
@login_required
def eliminar_detalle(request):
    detalles = Reserva.objects.all()

    if request.method == 'POST':
        detalle_id = request.POST.get('detalle')
        if detalle_id:
            detalle = get_object_or_404(Reserva, pk=detalle_id)
            detalle.delete()
            messages.success(request, f'Reserva #{detalle_id} eliminada correctamente.')
            return redirect('eliminar_detalle')
        else:
            messages.error(request, 'Debes seleccionar una reserva para eliminar.')

    return render(request, 'reservas/eliminar_detalle.html', {
        'detalles': detalles
    })


# ─────────────────────────────────────────────────────────────
# ACTUALIZAR MESA (vista HTML)
# ─────────────────────────────────────────────────────────────
@login_required
@login_required
def actualizar_mesa(request, mesa_id):
    mesas = Mesa.objects.all().order_by('numero_mesa')
    mesa = get_object_or_404(Mesa, numero_mesa=mesa_id)

    if request.method == 'POST':
        # Si cambió de mesa en el select, redirige sin guardar
        nueva_mesa_id = request.POST.get('mesa_id')
        if nueva_mesa_id and str(nueva_mesa_id) != str(mesa.numero_mesa):
            return redirect('actualizar_mesa', mesa_id=nueva_mesa_id)

        mesa.capacidad = request.POST.get('capacidad')
        mesa.ubicacion = request.POST.get('ubicacion')
        mesa.estado    = request.POST.get('estado')
        mesa.save()
        messages.success(request, f'Mesa {mesa.numero_mesa} actualizada correctamente.')
        return redirect('actualizar_mesa', mesa_id=mesa.numero_mesa)

    return render(request, 'reservas/actualizar_mesa.html', {
        'mesa':  mesa,
        'mesas': mesas,
    })
    
def listar_mesas_vista(request):
    mesas = Mesa.objects.all().order_by('numero_mesa')
    return render(request, 'reservas/listar_mesas.html', {'mesas': mesas})
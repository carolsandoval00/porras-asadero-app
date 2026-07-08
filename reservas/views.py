from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Reserva, Mesa
import json


# ─────────────────────────────────────────────────────────────
# HELPER DE PERMISOS
# ─────────────────────────────────────────────────────────────
def _es_cajero(request):
    return request.user.is_authenticated and request.user.rol == 'CAJERO' and not request.user.is_superuser

ACCESO_DENEGADO   = {'vista': 'sin_permisos'}
TEMPLATE_PERMISOS = 'usuarios/login.html'


# ─────────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────────────────────
@login_required
def reserva_view(request):
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    return render(request, 'reserva_inicio.html')


# ─────────────────────────────────────────────────────────────
# GUARDAR / ACTUALIZAR MESA DESDE EL JS
# ─────────────────────────────────────────────────────────────
@require_POST
@login_required
def mesa_guardar(request):
    if _es_cajero(request):
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
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
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    mesa = get_object_or_404(Mesa, numero_mesa=mesa_id)
    mesa.delete()
    messages.success(request, f'Mesa {mesa_id} eliminada correctamente.')
    return redirect('listar_mesas')


# ─────────────────────────────────────────────────────────────
# ELIMINAR DETALLE RESERVA
# ─────────────────────────────────────────────────────────────
@login_required
def eliminar_detalle(request):
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
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
    return render(request, 'reservas/eliminar_detalle.html', {'detalles': detalles})


# ─────────────────────────────────────────────────────────────
# EDITAR RESERVA
# ─────────────────────────────────────────────────────────────
@login_required
def editar_reserva(request, pk):
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    reserva = get_object_or_404(Reserva, pk=pk)
    mesas   = Mesa.objects.all().order_by('numero_mesa')
    if request.method == 'POST':
        reserva.nombre_cliente = request.POST.get('nombre_cliente', reserva.nombre_cliente)
        reserva.telefono       = request.POST.get('telefono', reserva.telefono)
        reserva.fecha          = request.POST.get('fecha', reserva.fecha)
        reserva.hora           = request.POST.get('hora', reserva.hora)
        reserva.num_personas   = request.POST.get('num_personas', reserva.num_personas)
        reserva.observaciones  = request.POST.get('observaciones', '')
        mesa_id = request.POST.get('mesa')
        if mesa_id:
            reserva.mesa = get_object_or_404(Mesa, pk=mesa_id)
        reserva.save()
        messages.success(request, f'Reserva #{reserva.pk} actualizada correctamente.')
        return redirect('crear_reserva')
    return render(request, 'reservas/editar_reserva.html', {'reserva': reserva, 'mesas': mesas})


# ─────────────────────────────────────────────────────────────
# ACTUALIZAR MESA (vista HTML)
# ─────────────────────────────────────────────────────────────
@login_required
def actualizar_mesa(request, mesa_id):
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    mesas = Mesa.objects.all().order_by('numero_mesa')
    mesa  = get_object_or_404(Mesa, numero_mesa=mesa_id)
    if request.method == 'POST':
        nueva_mesa_id = request.POST.get('mesa_id')
        if nueva_mesa_id and str(nueva_mesa_id) != str(mesa.numero_mesa):
            return redirect('actualizar_mesa', mesa_id=nueva_mesa_id)
        mesa.capacidad = request.POST.get('capacidad')
        mesa.ubicacion = request.POST.get('ubicacion')
        mesa.estado    = request.POST.get('estado')
        mesa.save()
        messages.success(request, f'Mesa {mesa.numero_mesa} actualizada correctamente.')
        return redirect('listar_mesas')
    return render(request, 'reservas/actualizar_mesa.html', {'mesa': mesa, 'mesas': mesas})


# ─────────────────────────────────────────────────────────────
# LISTAR MESAS
# ─────────────────────────────────────────────────────────────
@login_required
def listar_mesas_vista(request):
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    mesas = Mesa.objects.all().order_by('numero_mesa')
    return render(request, 'reservas/listar_mesas.html', {'mesas': mesas})


# ─────────────────────────────────────────────────────────────
# CREAR RESERVA
# ─────────────────────────────────────────────────────────────
@login_required
def crear_reserva(request):
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    context = {
        'reservas': Reserva.objects.all().order_by('-id'),
        'mesas':    Mesa.objects.all().order_by('numero_mesa'),
    }
    return render(request, 'reservas/crear_reserva.html', context)


# ─────────────────────────────────────────────────────────────
# DIAGRAMA DE MESAS
# ─────────────────────────────────────────────────────────────
@login_required
def diagrama_mesas(request):
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    return render(request, 'reservas/diagrama_mesas.html', {
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
    })


# ─────────────────────────────────────────────────────────────
# GESTIÓN DE MESAS
# ─────────────────────────────────────────────────────────────
@login_required
def gestion_mesas(request):
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    return render(request, 'reservas/gestion_mesas.html', {
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
    })
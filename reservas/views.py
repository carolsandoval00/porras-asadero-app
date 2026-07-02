from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Reserva, Mesa
import json


# ─────────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────────────────────
@login_required
def reserva_view(request):
    """
    Muestra la página de inicio del módulo de reservas.
    Solo la puede ver un usuario que ya inició sesión.
    """
    return render(request, 'reserva_inicio.html')


# ─────────────────────────────────────────────────────────────
# GUARDAR / ACTUALIZAR MESA DESDE EL JS
# ─────────────────────────────────────────────────────────────
@require_POST
@login_required
def mesa_guardar(request):
    """
    Guarda una mesa nueva o actualiza una que ya existe.

    Esta vista la llama el JavaScript del frontend (no un formulario
    normal), y le manda los datos en formato JSON.

    Cómo decide si crear o actualizar:
    - Si ya existe una mesa con ese mismo número, la actualiza.
    - Si no existe ninguna con ese número, crea una nueva.

    Datos que espera recibir: número de mesa, capacidad,
    ubicación y estado.

    Si todo sale bien, responde {'ok': True}.
    Si algo falla (por ejemplo faltó un dato), responde
    {'ok': False, 'error': 'mensaje del error'}.
    """
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
    """
    Borra una mesa según su número.

    También la llama el JavaScript del frontend cuando el usuario
    da clic en "eliminar" desde la pantalla de mesas.

    Después de borrarla, muestra un mensaje de éxito y devuelve
    al usuario a la lista de mesas.

    Si la mesa no existe, Django muestra automáticamente un
    error 404 (página no encontrada).
    """
    mesa = get_object_or_404(Mesa, numero_mesa=mesa_id)
    mesa.delete()
    messages.success(request, f'Mesa {mesa_id} eliminada correctamente.')
    return redirect('listar_mesas')


# ─────────────────────────────────────────────────────────────
# ELIMINAR DETALLE RESERVA
# ─────────────────────────────────────────────────────────────
@login_required
def eliminar_detalle(request):
    """
    Muestra todas las reservas y permite borrar una de la lista.

    Cuando el usuario solo entra a la página (GET), se le muestra
    la lista completa de reservas.

    Cuando el usuario manda el formulario (POST) eligiendo una
    reserva para borrar, esta vista la elimina y muestra un
    mensaje de éxito. Si no eligió ninguna, muestra un mensaje
    de error pidiéndole que seleccione una.
    """
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

    context = { 'detalles': detalles }
    return render(request, 'reservas/eliminar_detalle.html', context)


# ─────────────────────────────────────────────────────────────
# ACTUALIZAR MESA (vista HTML)
# ─────────────────────────────────────────────────────────────
@login_required
def actualizar_mesa(request, mesa_id):
    """
    Muestra el formulario para editar una mesa y guarda los cambios.

    Si el usuario solo entra a la página (GET), se le muestra el
    formulario con los datos actuales de la mesa.

    Si el usuario cambia la mesa en el selector del formulario
    (sin haber guardado todavía), lo manda a editar esa otra mesa
    en vez de guardar cambios en la mesa anterior por error.

    Si el usuario llena el formulario y lo envía (POST) para la
    mesa correcta, se guardan los nuevos datos: capacidad,
    ubicación y estado. Luego muestra un mensaje de éxito.
    """
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

    context = { 'mesa': mesa, 'mesas': mesas, }
    return render(request, 'reservas/actualizar_mesa.html', context)


def listar_mesas_vista(request):
    """
    Muestra todas las mesas registradas, ordenadas de menor a
    mayor número. Cualquier usuario puede ver esta lista (no pide
    inicio de sesión).
    """
    mesas = Mesa.objects.all().order_by('numero_mesa')
    context = {'mesas': mesas}
    return render(request, 'reservas/listar_mesas.html', context)


@login_required
def crear_reserva(request):
    """
    Muestra el formulario para crear una reserva nueva.

    Junto con el formulario, también le manda a la página la
    lista de reservas ya existentes (las más nuevas primero) y
    la lista de mesas disponibles, para que el usuario pueda
    elegir una mesa al reservar.
    """
    context = {
        'reservas': Reserva.objects.all().order_by('-id'),
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
    }
    return render(request, 'reservas/crear_reserva.html', context)


@login_required
def diagrama_mesas(request):
    """
    Muestra un diagrama visual de cómo están distribuidas las mesas.
    Le manda a la página la lista completa de mesas ordenadas por
    número, para que el diagrama las pueda dibujar.
    """
    context = {
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
    }
    return render(request, 'reservas/diagrama_mesas.html', context)


@login_required
def gestion_mesas(request):
    """
    Muestra el panel donde se administran las mesas: crear,
    editar y eliminar. Le manda a la página la lista completa
    de mesas ordenadas por número.
    """
    context = {
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
    }
    return render(request, 'reservas/gestion_mesas.html', context)
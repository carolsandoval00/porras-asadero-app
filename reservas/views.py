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
    """Muestra la página de inicio del módulo de reservas.

    Requiere que el usuario haya iniciado sesión.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.

    Returns:
        HttpResponse: Renderiza la plantilla ``reserva_inicio.html``.

    Raises:
        Http404: Si la plantilla no existe (comportamiento estándar
            de Django ante un template faltante).
    """
    return render(request, 'reserva_inicio.html')


# ─────────────────────────────────────────────────────────────
# GUARDAR / ACTUALIZAR MESA DESDE EL JS
# ─────────────────────────────────────────────────────────────
@require_POST
@login_required
def mesa_guardar(request):
    """Guarda una mesa nueva o actualiza una ya existente.

    Vista pensada para ser consumida por el JavaScript del
    frontend (no por un formulario HTML tradicional): recibe los
    datos en el cuerpo de la petición como JSON.

    Lógica de creación/actualización:
        - Si ya existe una mesa con ``numero_mesa`` igual al recibido,
          se actualiza.
        - Si no existe ninguna con ese número, se crea una nueva.

    Args:
        request (HttpRequest): Petición POST cuyo body debe ser un
            JSON con las claves:
                numero_mesa (int): Identificador/PK de la mesa.
                capacidad (int): Capacidad de personas de la mesa.
                ubicacion (str): Ubicación física de la mesa.
                estado (str): Estado actual de la mesa.

    Returns:
        JsonResponse: ``{'ok': True}`` con status 200 si la operación
            fue exitosa. ``{'ok': False, 'error': str}`` con status 400
            si ocurrió un error (por ejemplo, un campo faltante o un
            JSON inválido).

    Raises:
        KeyError: Si falta alguna de las claves requeridas en el JSON
            (capturado internamente y devuelto como respuesta 400).
        json.JSONDecodeError: Si el body no es un JSON válido
            (capturado internamente y devuelto como respuesta 400).
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
    """Elimina una mesa según su número (PK).

    También es invocada por el JavaScript del frontend cuando el
    usuario da clic en "eliminar" desde la pantalla de mesas.

    Args:
        request (HttpRequest): Petición POST del usuario autenticado.
        mesa_id (int): Valor de ``numero_mesa`` (primary key) de la
            mesa a eliminar.

    Returns:
        HttpResponseRedirect: Redirige a la vista ``listar_mesas``
            junto con un mensaje de éxito.

    Raises:
        Http404: Si no existe ninguna mesa con ese ``numero_mesa``
            (lanzado automáticamente por ``get_object_or_404``).
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
    """Lista las reservas existentes y permite eliminar una de ellas.

    En una petición GET simplemente muestra la lista completa de
    reservas. En una petición POST, elimina la reserva seleccionada
    por el usuario.

    Args:
        request (HttpRequest): Petición GET o POST. En POST debe
            incluir el campo de formulario ``detalle`` con el ID de
            la reserva a eliminar.

    Returns:
        HttpResponse: En GET, renderiza
            ``reservas/eliminar_detalle.html`` con el contexto
            ``{'detalles': <QuerySet de Reserva>}``.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``eliminar_detalle`` con un mensaje de éxito. Si no se
            seleccionó ninguna reserva, vuelve a renderizar la misma
            página con un mensaje de error.

    Raises:
        Http404: Si el ``detalle_id`` enviado no corresponde a
            ninguna reserva existente (lanzado por
            ``get_object_or_404``).
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
    """Muestra y procesa el formulario de edición de una mesa.

    En GET, muestra el formulario precargado con los datos actuales
    de la mesa indicada. En POST, guarda los cambios enviados. Si el
    usuario cambia de mesa en el selector del formulario sin haber
    guardado aún, la vista redirige a editar esa otra mesa en lugar
    de sobrescribir por error los datos de la mesa anterior. Tras
    guardar los cambios exitosamente, redirige al listado de mesas
    (``listar_mesas``) mostrando el mensaje de éxito, igual que el
    resto de acciones del módulo (eliminar mesa, eliminar reserva).

    Args:
        request (HttpRequest): Petición GET o POST. En POST puede
            incluir:
                mesa_id (str): Si difiere del ``mesa_id`` de la URL,
                    se interpreta como un cambio de selección y no
                    se guardan cambios.
                capacidad (str): Nueva capacidad de la mesa.
                ubicacion (str): Nueva ubicación de la mesa.
                estado (str): Nuevo estado de la mesa.
        mesa_id (int): Valor de ``numero_mesa`` (primary key) de la
            mesa a editar, tomado de la URL.

    Returns:
        HttpResponse: En GET, renderiza
            ``reservas/actualizar_mesa.html`` con el contexto
            ``{'mesa': <Mesa>, 'mesas': <QuerySet de Mesa>}``.
        HttpResponseRedirect: En POST, redirige a ``actualizar_mesa``
            si el usuario solo cambió de mesa en el selector (sin
            guardar), o a ``listar_mesas`` tras guardar los cambios
            exitosamente.

    Raises:
        Http404: Si no existe ninguna mesa con ese ``numero_mesa``
            (lanzado por ``get_object_or_404``).
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
        return redirect('listar_mesas')

    context = { 'mesa': mesa, 'mesas': mesas, }
    return render(request, 'reservas/actualizar_mesa.html', context)


def listar_mesas_vista(request):
    """Lista todas las mesas registradas, ordenadas por número.

    Vista pública: no requiere que el usuario haya iniciado sesión.

    Args:
        request (HttpRequest): Petición GET.

    Returns:
        HttpResponse: Renderiza ``reservas/listar_mesas.html`` con el
            contexto ``{'mesas': <QuerySet de Mesa ordenado por
            numero_mesa>}``.
    """
    mesas = Mesa.objects.all().order_by('numero_mesa')
    context = {'mesas': mesas}
    return render(request, 'reservas/listar_mesas.html', context)


@login_required
def crear_reserva(request):
    """Muestra el formulario de creación de una reserva nueva.

    Además del formulario, envía a la plantilla la lista de reservas
    ya existentes (las más recientes primero) y la lista de mesas
    disponibles, para que el usuario pueda elegir una al reservar.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.

    Returns:
        HttpResponse: Renderiza ``reservas/crear_reserva.html`` con el
            contexto:
                reservas (QuerySet[Reserva]): Todas las reservas,
                    ordenadas por ``-id`` (más nuevas primero).
                mesas (QuerySet[Mesa]): Todas las mesas, ordenadas por
                    ``numero_mesa``.
    """
    context = {
        'reservas': Reserva.objects.all().order_by('-id'),
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
    }
    return render(request, 'reservas/crear_reserva.html', context)


@login_required
def diagrama_mesas(request):
    """Muestra un diagrama visual de la distribución de las mesas.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.

    Returns:
        HttpResponse: Renderiza ``reservas/diagrama_mesas.html`` con
            el contexto ``{'mesas': <QuerySet de Mesa ordenado por
            numero_mesa>}``, usado por el frontend para dibujar el
            diagrama.
    """
    context = {
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
    }
    return render(request, 'reservas/diagrama_mesas.html', context)


@login_required
def gestion_mesas(request):
    """Muestra el panel de administración de mesas.

    Desde este panel se pueden crear, editar y eliminar mesas.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.

    Returns:
        HttpResponse: Renderiza ``reservas/gestion_mesas.html`` con
            el contexto ``{'mesas': <QuerySet de Mesa ordenado por
            numero_mesa>}``.
    """
    context = {
        'mesas': Mesa.objects.all().order_by('numero_mesa'),
    }
    return render(request, 'reservas/gestion_mesas.html', context)
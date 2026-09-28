import json
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import MesaForm, ReservaForm
from .models import Mesa, Reserva


# ─────────────────────────────────────────────────────────────
# HELPERS DE PERMISOS
# ─────────────────────────────────────────────────────────────
def _es_cajero(request):
    return (request.user.is_authenticated
            and request.user.rol == 'CAJERO'
            and not request.user.is_superuser)


def _es_cocinera(request):
    return (request.user.is_authenticated
            and request.user.rol == 'COCINERA'
            and not request.user.is_superuser)


def _sin_acceso(request):
    """El cajero puede consultar; la cocinera no entra al módulo."""
    return _es_cocinera(request)


def _solo_lectura(request):
    """Quien no puede crear/editar/eliminar reservas ni mesas."""
    return _es_cajero(request) or _es_cocinera(request)


ACCESO_DENEGADO = {'vista': 'sin_permisos'}
TEMPLATE_PERMISOS = 'usuarios/login.html'


def _error_json(mensaje, status=400):
    return JsonResponse({'ok': False, 'error': mensaje}, status=status)


def _errores_form(form):
    return '; '.join(
        f'{form.fields[campo].label or campo}: {", ".join(errores)}'
        if campo in form.fields else '; '.join(errores)
        for campo, errores in form.errors.items()
    )


def _parse_fecha(valor):
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────
# FILTRADO DE RESERVAS (lo usan la API y las vistas HTML)
# ─────────────────────────────────────────────────────────────
def filtrar_reservas(params):
    """
    Filtros admitidos:
      q       → nombre o teléfono
      estado  → PENDIENTE / CONFIRMADA / CANCELADA
      mesa    → número de mesa
      fecha   → hoy | futuras | pasadas | dia | mes | rango
      dia     → YYYY-MM-DD      (con fecha=dia)
      mes     → YYYY-MM         (con fecha=mes)
      desde   → YYYY-MM-DD      (con fecha=rango, o suelto)
      hasta   → YYYY-MM-DD      (con fecha=rango, o suelto)
    """
    qs = Reserva.objects.select_related('numero_mesa').all()

    q = (params.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(nombre_cliente__icontains=q) | Q(telefono__icontains=q))

    estado = (params.get('estado') or '').strip().upper()
    if estado:
        qs = qs.filter(estado=estado)

    mesa = (params.get('mesa') or '').strip()
    if mesa.isdigit():
        qs = qs.filter(numero_mesa_id=int(mesa))

    modo = (params.get('fecha') or '').strip().lower()
    hoy = date.today()

    if modo == 'hoy':
        qs = qs.filter(fecha_reserva=hoy)
    elif modo == 'futuras':
        qs = qs.filter(fecha_reserva__gte=hoy)
    elif modo == 'pasadas':
        qs = qs.filter(fecha_reserva__lt=hoy)
    elif modo == 'dia':
        dia = _parse_fecha(params.get('dia'))
        if dia:
            qs = qs.filter(fecha_reserva=dia)
    elif modo == 'mes':
        mes = (params.get('mes') or '').strip()   # YYYY-MM
        if len(mes) == 7 and mes[:4].isdigit() and mes[5:].isdigit():
            qs = qs.filter(fecha_reserva__year=int(mes[:4]),
                           fecha_reserva__month=int(mes[5:]))

    # El rango desde/hasta se aplica siempre que venga, combinable con lo anterior.
    desde = _parse_fecha(params.get('desde'))
    hasta = _parse_fecha(params.get('hasta'))
    if desde:
        qs = qs.filter(fecha_reserva__gte=desde)
    if hasta:
        qs = qs.filter(fecha_reserva__lte=hasta)

    return qs.order_by('fecha_reserva', 'hora_reserva')


# ─────────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────────────────────
@login_required
def reserva_view(request):
    if _sin_acceso(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    return render(request, 'reserva_inicio.html', {
        'nombre': request.user.get_full_name() or request.user.username,
        'puede_editar': not _solo_lectura(request),
    })


# ─────────────────────────────────────────────────────────────
# API JSON — RESERVAS
# ─────────────────────────────────────────────────────────────
@login_required
def api_reservas(request):
    if _sin_acceso(request):
        return _error_json('Sin permisos', 403)
    reservas = filtrar_reservas(request.GET)
    return JsonResponse({
        'ok': True,
        'reservas': [r.as_dict() for r in reservas],
        'total': reservas.count(),
    })


@login_required
def api_mesas(request):
    if _sin_acceso(request):
        return _error_json('Sin permisos', 403)
    return JsonResponse({
        'ok': True,
        'mesas': [m.as_dict() for m in Mesa.objects.all()],
    })


@require_POST
@login_required
def reserva_guardar(request):
    """Crea o actualiza una reserva desde el formulario JS."""
    if _solo_lectura(request):
        return _error_json('No tienes permisos para realizar esta acción', 403)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _error_json('Datos inválidos.')

    instancia = None
    reserva_id = data.get('id')
    if reserva_id:
        instancia = Reserva.objects.filter(pk=reserva_id).first()
        if instancia is None:
            return _error_json('La reserva que intentas editar ya no existe.', 404)

    form = ReservaForm(data, instance=instancia)
    if not form.is_valid():
        return _error_json(_errores_form(form))

    reserva = form.save()
    _sincronizar_estado_mesa(reserva.numero_mesa)
    return JsonResponse({'ok': True, 'reserva': reserva.as_dict()})


@require_POST
@login_required
def reserva_eliminar(request):
    if _solo_lectura(request):
        return _error_json('No tienes permisos para realizar esta acción', 403)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _error_json('Datos inválidos.')

    reserva = Reserva.objects.filter(pk=data.get('id')).first()
    if reserva is None:
        return _error_json('La reserva ya no existe.', 404)

    mesa = reserva.numero_mesa
    reserva.delete()
    _sincronizar_estado_mesa(mesa)
    return JsonResponse({'ok': True})


def _sincronizar_estado_mesa(mesa):
    """Marca la mesa como RESERVADA si tiene reservas activas de hoy en adelante."""
    if mesa is None:
        return
    tiene_activas = mesa.reservas.filter(
        estado__in=['PENDIENTE', 'CONFIRMADA'],
        fecha_reserva__gte=date.today(),
    ).exists()
    if tiene_activas and mesa.estado == 'LIBRE':
        mesa.estado = 'RESERVADA'
        mesa.save(update_fields=['estado'])
    elif not tiene_activas and mesa.estado == 'RESERVADA':
        mesa.estado = 'LIBRE'
        mesa.save(update_fields=['estado'])


# ─────────────────────────────────────────────────────────────
# API JSON — MESAS
# ─────────────────────────────────────────────────────────────
@require_POST
@login_required
def mesa_guardar(request):
    if _solo_lectura(request):
        return _error_json('No tienes permisos para realizar esta acción', 403)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _error_json('Datos inválidos.')

    numero = data.get('numero_mesa')
    existente = Mesa.objects.filter(numero_mesa=numero).first()
    form = MesaForm(data, instance=existente)
    if not form.is_valid():
        return _error_json(_errores_form(form))

    mesa = form.save()
    return JsonResponse({'ok': True, 'mesa': mesa.as_dict()})


@require_POST
@login_required
def mesa_eliminar(request):
    """Eliminación desde el JS (JSON). La vista HTML es eliminar_mesa_vista."""
    if _solo_lectura(request):
        return _error_json('No tienes permisos para realizar esta acción', 403)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _error_json('Datos inválidos.')

    mesa = Mesa.objects.filter(numero_mesa=data.get('numero_mesa')).first()
    if mesa is None:
        return _error_json('La mesa ya no existe.', 404)

    mesa.delete()   # las reservas asociadas caen en cascada
    return JsonResponse({'ok': True})


@require_POST
@login_required
def eliminar_mesa_vista(request, mesa_id):
    if _solo_lectura(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    mesa = get_object_or_404(Mesa, numero_mesa=mesa_id)
    mesa.delete()
    messages.success(request, f'Mesa {mesa_id} eliminada correctamente.')
    return redirect('listar_mesas')


# ─────────────────────────────────────────────────────────────
# ELIMINAR RESERVA (vista HTML)
# ─────────────────────────────────────────────────────────────
@login_required
def eliminar_detalle(request):
    if _solo_lectura(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    if request.method == 'POST':
        detalle_id = request.POST.get('detalle')
        if detalle_id:
            reserva = get_object_or_404(Reserva, pk=detalle_id)
            mesa = reserva.numero_mesa
            reserva.delete()
            _sincronizar_estado_mesa(mesa)
            messages.success(request, f'Reserva #{detalle_id} eliminada correctamente.')
            return redirect('eliminar_detalle')
        messages.error(request, 'Debes seleccionar una reserva para eliminar.')

    detalles = filtrar_reservas(request.GET)
    return render(request, 'reservas/eliminar_detalle.html', {
        'detalles': detalles,
        'filtros': {
            'q': request.GET.get('q', ''),
            'estado': request.GET.get('estado', ''),
            'fecha': request.GET.get('fecha', ''),
            'dia': request.GET.get('dia', ''),
            'mes': request.GET.get('mes', ''),
            'desde': request.GET.get('desde', ''),
            'hasta': request.GET.get('hasta', ''),
        },
        'estados': Reserva.ESTADO_RESERVA_CHOICES,
    })


# ─────────────────────────────────────────────────────────────
# CREAR / EDITAR RESERVA (vistas HTML con formulario Django)
# ─────────────────────────────────────────────────────────────
@login_required
def crear_reserva(request):
    if _solo_lectura(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            reserva = form.save()
            _sincronizar_estado_mesa(reserva.numero_mesa)
            messages.success(request, f'Reserva #{reserva.pk} creada correctamente.')
            return redirect('reserva_inicio')
        for campo, errores in form.errors.items():
            for error in errores:
                messages.error(request, f'{campo}: {error}')
    else:
        form = ReservaForm()

    return render(request, 'reservas/reserva_form.html', {
        'form': form,
        'reservas': filtrar_reservas(request.GET),
        'mesas': Mesa.objects.all(),
        'titulo': 'Nueva reserva',
    })


@login_required
def editar_reserva(request, pk):
    if _solo_lectura(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    reserva = get_object_or_404(Reserva, pk=pk)
    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            reserva = form.save()
            _sincronizar_estado_mesa(reserva.numero_mesa)
            messages.success(request, f'Reserva #{reserva.pk} actualizada correctamente.')
            return redirect('reserva_inicio')
        for campo, errores in form.errors.items():
            for error in errores:
                messages.error(request, f'{campo}: {error}')
    else:
        form = ReservaForm(instance=reserva)

    return render(request, 'reservas/reserva_form.html', {
        'form': form,
        'reserva': reserva,
        'mesas': Mesa.objects.all(),
        'titulo': f'Editar reserva #{reserva.pk}',
    })


# ─────────────────────────────────────────────────────────────
# MESAS (vistas HTML)
# ─────────────────────────────────────────────────────────────
@login_required
def actualizar_mesa(request, mesa_id):
    if _solo_lectura(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    mesas = Mesa.objects.all()
    mesa = get_object_or_404(Mesa, numero_mesa=mesa_id)

    if request.method == 'POST':
        nueva_mesa_id = request.POST.get('mesa_id')
        if nueva_mesa_id and str(nueva_mesa_id) != str(mesa.numero_mesa):
            return redirect('actualizar_mesa', mesa_id=nueva_mesa_id)
        form = MesaForm(request.POST, instance=mesa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Mesa {mesa.numero_mesa} actualizada correctamente.')
            return redirect('listar_mesas')
        for campo, errores in form.errors.items():
            for error in errores:
                messages.error(request, f'{campo}: {error}')
    else:
        form = MesaForm(instance=mesa)

    return render(request, 'reservas/actualizar_mesa.html',
                  {'mesa': mesa, 'mesas': mesas, 'form': form})


@login_required
def listar_mesas_vista(request):
    if _solo_lectura(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    mesas = Mesa.objects.all()
    if not mesas.exists():
        return render(request, 'reservas/sin_mesas.html')
    return render(request, 'reservas/listar_mesas.html', {'mesas': mesas})


@login_required
def diagrama_mesas(request):
    if _sin_acceso(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    return render(request, 'reservas/diagrama_mesas.html', {'mesas': Mesa.objects.all()})


@login_required
def gestion_mesas(request):
    if _solo_lectura(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    return render(request, 'reservas/gestion_mesas.html', {'mesas': Mesa.objects.all()})
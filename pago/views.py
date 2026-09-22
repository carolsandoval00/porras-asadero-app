from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from itertools import groupby
from datetime import datetime
from urllib.parse import urlencode
from .models import Pago, Caja
from .forms import PagoForm, CajaForm
from pedidos.models import Pedido


def _solo_cajero_admin(request):
    """Retorna True si el usuario NO tiene permiso (es mesero u otro rol no autorizado)."""
    return not (request.user.rol in ('ADMIN', 'CAJERO') or request.user.is_superuser)


# ── FILTRO POR FECHAS ───────────────────────────────────────────────

def _leer_rango(request, prefijo):
    """Lee las fechas del filtro desde el GET y bloquea fechas futuras.

    Args:
        request: Petición actual.
        prefijo (str): Prefijo de los parámetros ('p' pagos, 'o' órdenes, 'c' cajas).

    Returns:
        tuple: (desde, hasta) como objetos date o None.
    """
    hoy = timezone.localdate()

    def _parse(valor):
        try:
            fecha = datetime.strptime(valor, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return None
        return hoy if fecha > hoy else fecha

    desde = _parse(request.GET.get(f'{prefijo}_desde'))
    hasta = _parse(request.GET.get(f'{prefijo}_hasta'))
    if desde and hasta and desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


def _aplicar_rango(qs, campo, desde, hasta):
    """Filtra un queryset por rango de fechas sobre el campo indicado."""
    if desde:
        qs = qs.filter(**{f'{campo}__date__gte': desde})
    if hasta:
        qs = qs.filter(**{f'{campo}__date__lte': hasta})
    return qs


def _texto(fecha):
    """Devuelve la fecha en formato YYYY-MM-DD para los inputs, o cadena vacía."""
    return fecha.isoformat() if fecha else ''


def _query_pagos(desde, hasta):
    """Arma el querystring de los reportes para conservar el filtro de pagos."""
    params = {}
    if desde:
        params['p_desde'] = _texto(desde)
    if hasta:
        params['p_hasta'] = _texto(hasta)
    return urlencode(params)


def _contexto_listados(request):
    """Construye el contexto común de los tres listados ya filtrados por fecha."""
    p_desde, p_hasta = _leer_rango(request, 'p')
    o_desde, o_hasta = _leer_rango(request, 'o')
    c_desde, c_hasta = _leer_rango(request, 'c')

    ordenes_sin_pago = _aplicar_rango(
        Pedido.objects.exclude(estado='PAGADO'), 'fecha_creacion', o_desde, o_hasta
    ).order_by('-fecha_creacion')

    pagos_qs = _aplicar_rango(
        Pago.objects.select_related('pedido'), 'fecha_pago', p_desde, p_hasta
    ).order_by('-fecha_pago')

    cajas_qs = _aplicar_rango(
        Caja.objects.select_related('cajero'), 'fecha_apertura', c_desde, c_hasta
    ).order_by('fecha_apertura')

    pagos_por_fecha = []
    for fecha, grupo in groupby(pagos_qs, key=lambda p: p.fecha_pago.date()):
        items = list(grupo)
        pagos_por_fecha.append({
            'fecha': fecha,
            'pagos': items,
            'total': sum(p.monto for p in items),
            'count': len(items),
        })

    return {
        'pagos_por_fecha':  pagos_por_fecha,
        'ordenes_sin_pago': ordenes_sin_pago,
        'total_pagos':      pagos_qs.count(),
        'pagos_aprobados':  pagos_qs.count(),
        'pagos_pendientes': 0,
        'monto_total':      pagos_qs.aggregate(t=Sum('monto'))['t'] or 0,
        'cajas':            cajas_qs,
        'hoy':              _texto(timezone.localdate()),
        'p_desde':          _texto(p_desde),
        'p_hasta':          _texto(p_hasta),
        'o_desde':          _texto(o_desde),
        'o_hasta':          _texto(o_hasta),
        'c_desde':          _texto(c_desde),
        'c_hasta':          _texto(c_hasta),
        'filtro_pagos_qs':  _query_pagos(p_desde, p_hasta),
    }


@login_required
def pago_dashboard(request):
    if _solo_cajero_admin(request):
        return render(request, 'usuarios/login.html', {'vista': 'sin_permisos'})

    form_apertura = CajaForm()
    form = PagoForm()

    caja_activa = Caja.objects.filter(estado='ABIERTA').first()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'abrir_caja':
            if caja_activa:
                messages.error(
                    request,
                    f'Ya hay una caja abierta (Caja #{caja_activa.pk} — {caja_activa.cajero}. '
                    f'Debes cerrarla antes de abrir una nueva.'
                )
                return redirect('pago:dashboard')
            form_apertura = CajaForm(request.POST)
            if form_apertura.is_valid():
                apertura = form_apertura.save(commit=False)
                apertura.estado = 'ABIERTA'
                apertura.save()
                messages.success(request, ' Caja abierta correctamente.')
                return redirect('pago:dashboard')
            else:
                messages.error(request, ' Revisa los campos e intenta de nuevo.')

        elif action == 'cerrar_caja':
            caja_id = request.POST.get('caja_id')
            try:
                caja = Caja.objects.get(pk=caja_id, estado='ABIERTA')
                caja.estado = 'CERRADA'
                caja.fecha_cierre = timezone.now()
                caja.save()
                messages.success(request, ' Caja cerrada correctamente.')
            except Caja.DoesNotExist:
                messages.error(request, ' No se encontró la caja o ya está cerrada.')
            return redirect('pago:dashboard')

        elif action == 'editar_caja':
            caja_id       = request.POST.get('caja_id')
            observaciones = request.POST.get('observaciones', '').strip()
            try:
                caja = Caja.objects.get(pk=caja_id)
                caja.observaciones = observaciones
                caja.save()
                return JsonResponse({
                    'ok': True,
                    'observaciones': caja.observaciones or '—',
                })
            except Exception as e:
                return JsonResponse({'ok': False, 'error': str(e)}, status=400)

        else:
            post_data = request.POST.copy()
            pedido_id  = post_data.get('pedido')
            if pedido_id:
                try:
                    pedido = Pedido.objects.get(pk=pedido_id)
                    post_data['monto'] = pedido.total
                except Pedido.DoesNotExist:
                    pass
            form = PagoForm(post_data)
            if form.is_valid():
                pago = form.save(commit=False)
                if caja_activa:
                    pago.caja = caja_activa
                    pago.save()
                    pago.pedido.estado = 'PAGADO'
                    pago.pedido.save()
                    messages.success(request, 'Pedido registrado correctamente.', extra_tags='modal-pago')
                else:
                    messages.error(request, ' No puedes registrar pagos sin una caja abierta.')
                return redirect('pago:dashboard')

    context = _contexto_listados(request)
    context.update({
        'form':          form,
        'form_apertura': form_apertura,
        'nombre':        request.user.get_full_name() or request.user.username,
        'tab_activo':    request.GET.get('tab', 'pendientes'),
        'caja_activa':   caja_activa,
    })
    return render(request, 'pago/dashboard.html', context)


@login_required
def pago_editar(request, pk):
    if _solo_cajero_admin(request):
        return render(request, 'usuarios/login.html', {'vista': 'sin_permisos'})

    pago = get_object_or_404(Pago, pk=pk)
    form = PagoForm(request.POST or None, instance=pago)
    if form.is_valid():
        form.save()
        messages.success(request, ' Pago actualizado.')
        return redirect('pago:dashboard')
    context = {
        'form':   form,
        'pago':   pago,
        'nombre': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'pago/form.html', context)


@login_required
def pago_eliminar(request, pk):
    if _solo_cajero_admin(request):
        return render(request, 'usuarios/login.html', {'vista': 'sin_permisos'})

    pago = get_object_or_404(Pago, pk=pk)
    if request.method == 'POST':
        pago.delete()
        messages.success(request, ' Pago eliminado.')
    return redirect('pago:dashboard')


@login_required
def caja_detalle(request, pk):
    if _solo_cajero_admin(request):
        return render(request, 'usuarios/login.html', {'vista': 'sin_permisos'})

    caja_seleccionada = get_object_or_404(Caja, pk=pk)
    pagos_caja = Pago.objects.filter(caja=caja_seleccionada).select_related('pedido').order_by('-fecha_pago')

    total_ingresos   = pagos_caja.aggregate(t=Sum('monto'))['t'] or 0
    total_pendientes = 0

    context = _contexto_listados(request)
    context.update({
        'form':               PagoForm(),
        'form_apertura':      CajaForm(),
        'nombre':             request.user.get_full_name() or request.user.username,
        'caja_seleccionada':  caja_seleccionada,
        'pagos_caja':         pagos_caja,
        'total_ingresos':     total_ingresos,
        'total_pendientes':   total_pendientes,
        'saldo_final':        caja_seleccionada.monto_inicial + total_ingresos,
        'tab_activo':         'detalle-caja',
        'caja_activa':        Caja.objects.filter(estado='ABIERTA').first(),
    })
    return render(request, 'pago/dashboard.html', context)


# ── REPORTES ────────────────────────────────────────────────────────

def _pagos_reporte_queryset(request):
    """Queryset de pagos para los reportes, respetando el filtro de fechas."""
    desde, hasta = _leer_rango(request, 'p')
    qs = Pago.objects.select_related('pedido', 'pedido__cliente')
    return _aplicar_rango(qs, 'fecha_pago', desde, hasta).order_by('-fecha_pago')


def _rango_texto(request):
    """Texto legible del rango aplicado, para el encabezado de los reportes."""
    desde, hasta = _leer_rango(request, 'p')
    if desde and hasta:
        return f'Del {desde.strftime("%d/%m/%Y")} al {hasta.strftime("%d/%m/%Y")}'
    if desde:
        return f'Desde el {desde.strftime("%d/%m/%Y")}'
    if hasta:
        return f'Hasta el {hasta.strftime("%d/%m/%Y")}'
    return 'Todas las fechas'


@login_required
def pagos_exportar_excel(request):
    if _solo_cajero_admin(request):
        return render(request, 'usuarios/login.html', {'vista': 'sin_permisos'})

    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    pagos = _pagos_reporte_queryset(request)
    wb = Workbook()
    ws = wb.active
    ws.title = 'Pagos registrados'

    encabezados = ['Orden', 'Cliente', 'Método', 'Monto', 'Referencia', 'Estado', 'Fecha', 'Hora']
    ws.append(encabezados)
    for col in range(1, len(encabezados) + 1):
        celda = ws.cell(row=1, column=col)
        celda.font      = Font(bold=True, color='F5ECD7')
        celda.fill      = PatternFill(start_color='C0392B', end_color='C0392B', fill_type='solid')
        celda.alignment = Alignment(horizontal='center')

    for pg in pagos:
        ws.append([
            pg.pedido.numero_orden if pg.pedido else '—',
            pg.pedido.cliente.nombre_completo if pg.pedido and pg.pedido.cliente else '—',
            pg.get_metodo_pago_display(),
            float(pg.monto),
            pg.referencia or '—',
            'Pagado',
            pg.fecha_pago.strftime('%d/%m/%Y'),
            pg.fecha_pago.strftime('%I:%M %p'),
        ])

    for i, ancho in enumerate([14, 26, 16, 12, 20, 12, 14, 12], start=1):
        ws.column_dimensions[chr(64 + i)].width = ancho

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="pagos_registrados.xlsx"'
    wb.save(response)
    return response


@login_required
def pagos_exportar_pdf(request):
    if _solo_cajero_admin(request):
        return render(request, 'usuarios/login.html', {'vista': 'sin_permisos'})

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    pagos = _pagos_reporte_queryset(request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="pagos_registrados.pdf"'

    doc = SimpleDocTemplate(
        response, pagesize=landscape(letter),
        topMargin=1.2*cm, bottomMargin=1.2*cm,
        leftMargin=1.2*cm, rightMargin=1.2*cm,
    )
    estilos   = getSampleStyleSheet()
    elementos = [
        Paragraph('Porras Asadero — Pagos registrados', estilos['Title']),
        Paragraph(f'Generado el {timezone.now().strftime("%d/%m/%Y %I:%M %p")}', estilos['Normal']),
        Paragraph(f'Rango: {_rango_texto(request)}', estilos['Normal']),
        Spacer(1, 0.5*cm),
    ]

    datos = [['Orden', 'Cliente', 'Método', 'Monto', 'Referencia', 'Estado', 'Fecha', 'Hora']]
    total = 0
    for pg in pagos:
        total += pg.monto
        datos.append([
            pg.pedido.numero_orden if pg.pedido else '—',
            pg.pedido.cliente.nombre_completo if pg.pedido and pg.pedido.cliente else '—',
            pg.get_metodo_pago_display(),
            f'${pg.monto:,.0f}',
            pg.referencia or '—',
            'Pagado',
            pg.fecha_pago.strftime('%d/%m/%Y'),
            pg.fecha_pago.strftime('%I:%M %p'),
        ])
    datos.append(['', '', '', f'${total:,.0f}', '', '', '', ''])

    tabla = Table(datos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0),  (-1, 0),  colors.HexColor('#C0392B')),
        ('TEXTCOLOR',     (0, 0),  (-1, 0),  colors.HexColor('#F5ECD7')),
        ('FONTNAME',      (0, 0),  (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0),  (-1, -1), 8.5),
        ('ALIGN',         (3, 1),  (3, -1),  'RIGHT'),
        ('GRID',          (0, 0),  (-1, -1), 0.5, colors.HexColor('#D4C4A0')),
        ('ROWBACKGROUNDS',(0, 1),  (-1, -2), [colors.HexColor('#FDF7EC'), colors.HexColor('#F5ECD7')]),
        ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND',    (0, -1), (-1, -1), colors.HexColor('#F5ECD7')),
    ]))
    elementos.append(tabla)
    doc.build(elementos)
    return response


@login_required
def pagos_imprimir(request):
    if _solo_cajero_admin(request):
        return render(request, 'usuarios/login.html', {'vista': 'sin_permisos'})

    pagos = _pagos_reporte_queryset(request)
    return render(request, 'pago/pagos_imprimir.html', {
        'pagos':  pagos,
        'ahora':  timezone.now(),
        'rango':  _rango_texto(request),
        'total':  pagos.aggregate(t=Sum('monto'))['t'] or 0,
    })
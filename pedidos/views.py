import calendar
import csv
import json
from datetime import date, timedelta
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
<<<<<<< Updated upstream
from django.db.models import Q
=======
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
>>>>>>> Stashed changes
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from usuarios.models import Cliente

from .forms import CategoriaForm, ClienteForm, PedidoForm, ProductoForm
from .models import Categoria, Pedido, PedidoItem, Producto

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# ── ENCABEZADO CON LOGO PARA LOS REPORTES PDF ───────────────────────
import io
from datetime import datetime

from django.conf import settings
from PIL import Image as PILImage
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.platypus import Image as RLImage

_LOGO_PATH = settings.BASE_DIR / 'static' / 'img' / 'logo.png'
_LOGO_ALTO = 2.6 * cm
_logo_cache = {}

def _logo_recortado():
    """Abre static/img/logo.png, le quita el espacio en blanco sobrante y lo
    reduce de tamaño para que el PDF no pese tanto. Se calcula una sola vez."""
    if 'logo' not in _logo_cache:
        try:
            img = PILImage.open(_LOGO_PATH).convert('RGBA')
            fondo = PILImage.new('RGB', img.size, (255, 255, 255))
            fondo.paste(img, mask=img.split()[3])
            # recorte al contenido (todo lo que no sea blanco)
            caja = PILImage.eval(fondo.convert('L'), lambda v: 255 if v < 245 else 0).getbbox()
            if caja:
                fondo = fondo.crop(caja)
            ancho = 600
            fondo = fondo.resize((ancho, round(fondo.height * ancho / fondo.width)), PILImage.LANCZOS)
            buf = io.BytesIO()
            fondo.save(buf, format='PNG', optimize=True)
            _logo_cache['logo'] = (buf.getvalue(), fondo.width / fondo.height)
        except Exception:
            _logo_cache['logo'] = None
    return _logo_cache['logo']


def encabezado_reporte(titulo):
    """Lista inicial de elementos del PDF: logo a la izquierda, título y
    fecha a la derecha, y una línea roja debajo."""
    styles = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle('TituloReporte', parent=styles['Title'], alignment=TA_LEFT,
        fontSize=18, leading=22, textColor=colors.HexColor('#C0392B'))
    estilo_sub = ParagraphStyle('SubReporte', parent=styles['Normal'], fontSize=9,
        textColor=colors.HexColor('#555555'))
    texto = [
        Paragraph(titulo, estilo_titulo),
        Paragraph(f"Porras Asadero · Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_sub),
    ]
    logo = _logo_recortado()
    if logo:
        datos, proporcion = logo
        ancho_logo = _LOGO_ALTO * proporcion
        celda_logo = RLImage(io.BytesIO(datos), width=ancho_logo, height=_LOGO_ALTO)
    else:  # si no encuentra el logo, el reporte sale igual, solo con texto
        ancho_logo, celda_logo = 0.1 * cm, ''
    cabecera = Table([[celda_logo, texto]], colWidths=[ancho_logo + 0.5*cm, 26.7*cm - ancho_logo - 0.5*cm])
    cabecera.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('LINEBELOW', (0,0), (-1,0), 1.2, colors.HexColor('#C0392B')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    return [cabecera, Spacer(1, 0.5*cm)]



def _respuesta_excel(titulo, nombre_archivo, encabezados, filas, anchos, cols_dinero=()):
    """Genera un .xlsx con el logo arriba a la izquierda, el título al lado,
    y la tabla con los mismos colores del PDF. `cols_dinero` son los índices
    (empezando en 0) de las columnas que llevan formato $."""
    wb = Workbook()
    ws = wb.active
    ws.title = titulo[:31]
    n = len(encabezados)

    for i, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    # Logo (arriba a la izquierda)
    ancho_logo_px = 0
    logo = _logo_recortado()
    if logo:
        datos, proporcion = logo
        img = XLImage(io.BytesIO(datos))
        img.height = 80
        img.width = round(80 * proporcion)
        ws.add_image(img, 'A1')
        ancho_logo_px = img.width

    # El título va en la primera columna que quede libre a la derecha del logo
    acumulado, col_titulo = 0, 1
    for i, ancho in enumerate(anchos, start=1):
        acumulado += ancho * 7 + 5
        col_titulo = i + 1
        if acumulado >= ancho_logo_px + 8:
            break
    col_titulo = min(col_titulo, max(n, 2))

    ws.row_dimensions[2].height = 26
    ws.row_dimensions[3].height = 16
    c = ws.cell(row=2, column=col_titulo, value=titulo)
    c.font = Font(name='Calibri', size=16, bold=True, color='C0392B')
    c.alignment = Alignment(vertical='center')
    c = ws.cell(row=3, column=col_titulo,
                value=f"Porras Asadero · Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    c.font = Font(name='Calibri', size=9, color='555555')

    # Encabezados de la tabla (fila 6)
    fila_enc = 6
    borde = Border(*(Side(style='thin', color='D4C4A0'),) * 4)
    for j, texto in enumerate(encabezados, start=1):
        cel = ws.cell(row=fila_enc, column=j, value=texto)
        cel.font = Font(name='Calibri', size=10, bold=True, color='F5ECD7')
        cel.fill = PatternFill('solid', fgColor='C0392B')
        cel.alignment = Alignment(vertical='center', horizontal='left')
        cel.border = borde
    ws.row_dimensions[fila_enc].height = 20

    # Filas de datos con fondo alternado
    claros = ('FDF7EC', 'EDE3C8')
    for i, fila in enumerate(filas):
        r = fila_enc + 1 + i
        for j, valor in enumerate(fila, start=1):
            if (j - 1) in cols_dinero and valor is not None:
                valor = float(valor)
            cel = ws.cell(row=r, column=j, value=valor)
            cel.font = Font(name='Calibri', size=10)
            cel.fill = PatternFill('solid', fgColor=claros[i % 2])
            cel.border = borde
            cel.alignment = Alignment(vertical='center', wrap_text=True)
            if (j - 1) in cols_dinero:
                cel.number_format = '"$"#,##0'

    ws.freeze_panes = ws.cell(row=fila_enc + 1, column=1)
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f'{fila_enc}:{fila_enc}'

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    wb.save(response)
    return response


# ── HELPERS DE PERMISOS ─────────────────────────────────────────────

TEMPLATE_PERMISOS = 'usuarios/login.html'
ACCESO_DENEGADO   = {'vista': 'sin_permisos'}

def _es_cajero(request):
    """El cajero solo puede ver pedidos, nada más."""
    return request.user.is_authenticated and request.user.rol == 'CAJERO' and not request.user.is_superuser

def _es_mesero(request):
    """El mesero solo puede ver/crear/editar pedidos y reservas."""
    return request.user.is_authenticated and request.user.rol == 'MESERO' and not request.user.is_superuser

def _es_cocinera(request):
    """La cocinera solo puede ver los pedidos y marcarlos como listos."""
    return request.user.is_authenticated and request.user.rol == 'COCINERA' and not request.user.is_superuser

def _solo_admin(request):
    """Solo admin puede ver productos, categorías, clientes y órdenes."""
    return not (request.user.rol == 'ADMIN' or request.user.is_superuser)


# ── HELPERS PRIVADOS ────────────────────────────────────────────────

def _productos_disponibles():
    return (
        Producto.objects
        .filter(disponible=True)
        .select_related('categoria')
        .order_by('categoria__nombre', 'nombre')
    )


def _parse_items_from_post(request):
    items_data = []
    i = 0
    while True:
        producto_id = request.POST.get(f'items[{i}][id]')
        if producto_id is None:
            break
        try:
            producto = Producto.objects.get(pk=producto_id, disponible=True)
            cantidad = int(request.POST.get(f'items[{i}][cantidad]', 1))
            if cantidad > 0:
                items_data.append({'producto': producto, 'cantidad': cantidad})
        except (Producto.DoesNotExist, ValueError):
            pass
        i += 1
    return items_data


def _items_as_json(pedido):
    items = [
        {
            'id': str(item.producto.pk),
            'nombre': item.producto.nombre,
            'precio': int(item.precio_unitario),
            'cantidad': item.cantidad,
        }
        for item in pedido.items.select_related('producto').all()
    ]
    return json.dumps(items, ensure_ascii=False)


def _resolver_filtro_fecha(request):
    """Lee el filtro de fechas del GET (mismo esquema que el de Reservas:
    Todas / Hoy / Próximas / Pasadas / Día específico / Mes específico / Rango)
    y calcula el rango real (efectivo_desde/efectivo_hasta) que hay que aplicar
    a la consulta. Nunca permite que los campos manuales caigan después de hoy.
    """
    hoy_date = timezone.localdate()
    hoy = hoy_date.isoformat()

    filtro_fecha = request.GET.get('filtro_fecha', '').strip()
    fecha_dia    = request.GET.get('fecha_dia', '').strip()
    fecha_mes    = request.GET.get('fecha_mes', '').strip()  # formato 'YYYY-MM'
    fecha_desde  = request.GET.get('fecha_desde', '').strip()
    fecha_hasta  = request.GET.get('fecha_hasta', '').strip()

    if fecha_desde and fecha_desde > hoy:
        fecha_desde = hoy
    if fecha_hasta and fecha_hasta > hoy:
        fecha_hasta = hoy
    if fecha_dia and fecha_dia > hoy:
        fecha_dia = hoy

    efectivo_desde = ''
    efectivo_hasta = ''

    if filtro_fecha == 'hoy':
        efectivo_desde = efectivo_hasta = hoy
    elif filtro_fecha == 'futuras':
        efectivo_desde = hoy
    elif filtro_fecha == 'pasadas':
        efectivo_hasta = (hoy_date - timedelta(days=1)).isoformat()
    elif filtro_fecha == 'dia' and fecha_dia:
        efectivo_desde = efectivo_hasta = fecha_dia
    elif filtro_fecha == 'mes' and fecha_mes:
        try:
            anio, mes = (int(parte) for parte in fecha_mes.split('-'))
            primer_dia = date(anio, mes, 1)
            ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])
            efectivo_desde = primer_dia.isoformat()
            efectivo_hasta = min(ultimo_dia.isoformat(), hoy) if ultimo_dia.isoformat() > hoy else ultimo_dia.isoformat()
        except (ValueError, TypeError):
            pass
    elif filtro_fecha == 'rango':
        efectivo_desde = fecha_desde
        efectivo_hasta = fecha_hasta
    # filtro_fecha == '' (Todas las fechas) -> sin límites

    return {
        'filtro_fecha': filtro_fecha,
        'fecha_dia': fecha_dia,
        'fecha_mes': fecha_mes,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'efectivo_desde': efectivo_desde,
        'efectivo_hasta': efectivo_hasta,
    }


def _pedidos_filtrados(request):
    q = request.GET.get('q', '').strip()
    filtro = _resolver_filtro_fecha(request)

    qs = (
        Pedido.objects
        .select_related('cliente', 'mesero', 'mesa')
        .prefetch_related('items__producto')
        .order_by('-fecha_creacion')
    )
    if q:
        qs = qs.filter(
            Q(cliente__nombre_completo__icontains=q) | Q(descripcion__icontains=q)
        )
    if filtro['efectivo_desde']:
        qs = qs.filter(fecha_creacion__date__gte=filtro['efectivo_desde'])
    if filtro['efectivo_hasta']:
        qs = qs.filter(fecha_creacion__date__lte=filtro['efectivo_hasta'])
    return qs


# ── INVENTARIO DE BEBIDAS: HELPERS ──────────────────────────────────

CATEGORIA_BEBIDAS = 'Bebidas'   # nombre de la categoría que se controla en el inventario
LIMITE_STOCK      = 100000


class StockInsuficiente(Exception):
    """Se lanza cuando un pedido pide más unidades de las que hay en inventario."""


def _bebidas():
    """Productos de la categoría 'Bebidas' (sin importar mayúsculas)."""
    return Producto.objects.filter(categoria__nombre__iexact=CATEGORIA_BEBIDAS)


def _destino_seguro(request, por_defecto):
    """Usa el campo 'next' del formulario solo si apunta a este mismo sitio."""
    destino = request.POST.get('next', '')
    if destino and url_has_allowed_host_and_scheme(
            destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destino
    return reverse(por_defecto)


def _pares_de_items(items_data):
    """[(producto_pk, cantidad)] a partir de lo que llega del formulario."""
    return [(it['producto'].pk, it['cantidad']) for it in items_data]


def _pares_de_pedido(pedido):
    """[(producto_pk, cantidad)] a partir de los items ya guardados del pedido."""
    return [(it.producto_id, it.cantidad) for it in pedido.items.all()]


def _mover_stock(pares, signo):
    """Suma (signo=+1) o resta (signo=-1) unidades al inventario.
    Solo afecta a los productos con stock configurado.
    Debe llamarse dentro de transaction.atomic()."""
    for pk, cantidad in pares:
        p = Producto.objects.select_for_update().get(pk=pk)
        if p.stock_actual is None:
            continue
        nuevo = p.stock_actual + signo * cantidad
        if nuevo < 0:
            raise StockInsuficiente(
                f'❌ No hay suficiente "{p.nombre}": quedan {p.stock_actual}.')
        p.stock_actual = nuevo
        p.save(update_fields=['stock_actual'])


def _eliminar_pedido_con_stock(pedido):
    """Borra el pedido y devuelve al inventario las unidades que había descontado."""
    with transaction.atomic():
        _mover_stock(_pares_de_pedido(pedido), +1)
        pedido.delete()


# ── TABLERO PRINCIPAL (DASHBOARD) ──────────────────────────────────

@login_required
def dashboard(request):
    # La cocinera no tiene un tablero propio: va directo a Ver Órdenes.
    if _es_cocinera(request):
        return redirect('pedidos:orden_lista')

    total_pedidos      = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado='PREPARACION').count()
    total_productos    = Producto.objects.count()
    total_categorias   = Categoria.objects.count()
    total_clientes     = Cliente.objects.count()

    ultimos_pedidos = list(
        Pedido.objects
        .select_related('cliente', 'mesero', 'mesa')
        .order_by('-fecha_creacion')[:5]
    )

    return render(request, 'pedidos/dashboard.html', {
        'titulo': 'Pedidos',
        'total_pedidos': total_pedidos,
        'pedidos_pendientes': pedidos_pendientes,
        'total_ordenes': total_pedidos,
        'total_productos': total_productos,
        'total_categorias': total_categorias,
        'total_clientes': total_clientes,
        'ultimos_pedidos': ultimos_pedidos,
    })


# ── GESTIÓN DE PEDIDOS ───────────────────────────────────────────────

@login_required
def pedido_lista(request):
    if _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    q          = request.GET.get('q', '').strip()
    filtro     = _resolver_filtro_fecha(request)
    pedidos_qs = _pedidos_filtrados(request)
    pedidos_lista_data = list(pedidos_qs)
    pedidos_por_fecha  = []
    for fecha, grupo in groupby(pedidos_lista_data, key=lambda p: p.fecha_creacion.date()):
        items = list(grupo)
        pedidos_por_fecha.append({'fecha': fecha, 'pedidos': items, 'count': len(items)})
    return render(request, 'pedidos/pedido_lista.html', {
        'titulo': 'Pedidos',
        'pedidos_por_fecha': pedidos_por_fecha,
        'q': q,
        'filtro_fecha': filtro['filtro_fecha'],
        'fecha_dia': filtro['fecha_dia'],
        'fecha_mes': filtro['fecha_mes'],
        'fecha_desde': filtro['fecha_desde'],
        'fecha_hasta': filtro['fecha_hasta'],
        'seccion_activa': 'pedido-lista',
    })


@login_required
def pedido_marcar_listo(request, pk):
    """La cocinera (y el admin) marcan un pedido en preparación como listo,
    quedando disponible para pago en 'Órdenes por pagar'."""
    # Solo cocinera y admin pueden usar esta acción; cajero y mesero no.
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        if pedido.estado == 'PREPARACION':
            pedido.estado = 'SERVIDO'
            pedido.save(update_fields=['estado'])
            messages.success(request, f'✅ Pedido {pedido.numero_pedido} marcado como listo.')
        else:
            messages.error(request, '❌ Este pedido ya no está en preparación.')
    return redirect('pedidos:orden_lista')


@login_required
def pedido_exportar_pdf(request):
    pedidos_qs = _pedidos_filtrados(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="pedidos.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles   = getSampleStyleSheet()
    elements = encabezado_reporte("Reporte de Pedidos")
    data = [['#', 'Cliente', 'Mesa', 'Productos', 'Estado', 'Total', 'Fecha']]
    for p in pedidos_qs:
        productos_str = ', '.join(f"{it.cantidad}x {it.producto.nombre}" for it in p.items.all()) or '—'
        data.append([p.numero_pedido, str(p.cliente), str(p.mesa) if p.mesa else '—',
            Paragraph(productos_str, styles['Normal']), p.get_estado_display(),
            f"${p.total:,.0f}", p.fecha_creacion.strftime('%d/%m/%Y %H:%M')])
    tabla = Table(data, colWidths=[1.8*cm, 4*cm, 2.5*cm, 7.5*cm, 3*cm, 2.5*cm, 4*cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#C0392B')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#F5ECD7')),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,0),9),
        ('FONTSIZE',(0,1),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#FDF7EC'),colors.HexColor('#EDE3C8')]),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#D4C4A0')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'), ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5), ('LEFTPADDING',(0,0),(-1,-1),5),
        ('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))
    elements.append(tabla)
    doc.build(elements)
    return response


@login_required
def pedido_exportar_excel(request):
    pedidos_qs = _pedidos_filtrados(request)
    filas = []
    for p in pedidos_qs:
        productos_str = ', '.join(f"{it.cantidad}x {it.producto.nombre}" for it in p.items.all()) or '—'
        filas.append([p.numero_pedido, str(p.cliente), str(p.mesa) if p.mesa else '—',
            productos_str, p.descripcion or '—', p.get_estado_display(),
            p.total, p.fecha_creacion.strftime('%d/%m/%Y %H:%M')])
    return _respuesta_excel("Reporte de Pedidos", "pedidos.xlsx",
        ['#', 'Cliente', 'Mesa', 'Productos', 'Descripción', 'Estado', 'Total', 'Fecha'],
        filas, [10, 24, 12, 45, 30, 16, 14, 18], cols_dinero=(6,))


@login_required
def pedido_crear(request):
    # Cajero NO puede crear pedidos
    if _es_cajero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    productos_disponibles = _productos_disponibles()
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.mesero        = request.user
            pedido.fecha_creacion = timezone.now()
            pedido.estado        = 'PREPARACION'
            items_data = _parse_items_from_post(request)
            if not items_data:
                messages.error(request, '❌ Agrega al menos un producto al pedido.')
                return render(request, 'pedidos/pedido_form.html', {
                    'form': form, 'productos_disponibles': productos_disponibles,
                    'seccion_activa': 'pedido-crear'})
            total = sum(it['producto'].precio * it['cantidad'] for it in items_data)
            pedido.total = total; pedido.subtotal = total; pedido.impuestos = 0
            try:
                # Todo o nada: si falta stock de una bebida, no se guarda nada
                with transaction.atomic():
                    pedido.save()
                    PedidoItem.objects.bulk_create([
                        PedidoItem(pedido=pedido, producto=it['producto'],
                            cantidad=it['cantidad'], precio_unitario=it['producto'].precio)
                        for it in items_data])
                    _mover_stock(_pares_de_items(items_data), -1)
            except StockInsuficiente as e:
                messages.error(request, str(e))
                return render(request, 'pedidos/pedido_form.html', {
                    'form': form, 'productos_disponibles': productos_disponibles,
                    'seccion_activa': 'pedido-crear'})
            messages.success(request, f'✅ Pedido {pedido.numero_pedido} creado correctamente.')
            return redirect('pedidos:pedido_lista')
        messages.error(request, '❌ Corrige los errores en el formulario de pedido.')
        return render(request, 'pedidos/pedido_form.html', {
            'form': form, 'productos_disponibles': productos_disponibles,
            'seccion_activa': 'pedido-crear'})
    form = PedidoForm()
    return render(request, 'pedidos/pedido_form.html', {
        'form': form, 'productos_disponibles': productos_disponibles,
        'seccion_activa': 'pedido-crear'})


@login_required
def pedido_editar(request, pk):
    # Cajero NO puede editar pedidos
    if _es_cajero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    pedido                = get_object_or_404(Pedido, pk=pk)
    productos_disponibles = _productos_disponibles()
    if request.method == 'POST':
        items_data = _parse_items_from_post(request)
        form       = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            p = form.save(commit=False)
            if items_data:
                total = sum(it['producto'].precio * it['cantidad'] for it in items_data)
                try:
                    # Todo o nada: devuelve lo del pedido viejo, guarda el nuevo y descuenta
                    with transaction.atomic():
                        _mover_stock(_pares_de_pedido(pedido), +1)
                        p.total = total; p.subtotal = total; p.save()
                        pedido.items.all().delete()
                        PedidoItem.objects.bulk_create([
                            PedidoItem(pedido=pedido, producto=it['producto'],
                                cantidad=it['cantidad'], precio_unitario=it['producto'].precio)
                            for it in items_data])
                        _mover_stock(_pares_de_items(items_data), -1)
                except StockInsuficiente as e:
                    messages.error(request, str(e))
                    return render(request, 'pedidos/pedido_form.html', {
                        'form': form, 'pedido': pedido,
                        'pedido_items_json': _items_as_json(pedido),
                        'productos_disponibles': productos_disponibles,
                        'seccion_activa': 'pedido-editar'})
            else:
                p.save()
            messages.success(request, 'Pedido actualizado correctamente.')
            return redirect('pedidos:pedido_lista')
        return render(request, 'pedidos/pedido_form.html', {
            'form': form, 'pedido': pedido,
            'pedido_items_json': _items_as_json(pedido),
            'productos_disponibles': productos_disponibles,
            'seccion_activa': 'pedido-editar'})
    form = PedidoForm(instance=pedido)
    return render(request, 'pedidos/pedido_form.html', {
        'form': form, 'pedido': pedido,
        'pedido_items_json': _items_as_json(pedido),
        'productos_disponibles': productos_disponibles,
        'seccion_activa': 'pedido-editar'})


@login_required
def pedido_eliminar(request, pk):
    # Cajero NO puede eliminar pedidos
    if _es_cajero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        _eliminar_pedido_con_stock(pedido)
        messages.success(request, '🗑️ Pedido eliminado.')
    return redirect('pedidos:pedido_lista')


# ── GESTIÓN DE ÓRDENES ──────────────────────────────────────────────

@login_required
def orden_lista(request):
    # Cajero y Mesero NO pueden ver órdenes; la cocinera sí (es su pantalla de trabajo).
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    q_orden = request.GET.get('q_orden', '').strip()
    filtro = _resolver_filtro_fecha(request)
    ordenes_qs = _ordenes_filtradas(request)
    ordenes_lista_data = list(ordenes_qs)
    ordenes_por_fecha  = []
    for fecha, grupo in groupby(ordenes_lista_data, key=lambda o: o.fecha_creacion.date()):
        items = list(grupo)
        ordenes_por_fecha.append({'fecha': fecha, 'ordenes': items, 'count': len(items)})
    return render(request, 'pedidos/orden_lista.html', {
        'titulo': 'Pedidos', 'ordenes_por_fecha': ordenes_por_fecha,
        'q_orden': q_orden,
        'filtro_fecha': filtro['filtro_fecha'],
        'fecha_dia': filtro['fecha_dia'],
        'fecha_mes': filtro['fecha_mes'],
        'fecha_desde': filtro['fecha_desde'],
        'fecha_hasta': filtro['fecha_hasta'],
        'seccion_activa': 'orden-lista'})


@login_required
def orden_detalle(request, pk):
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    orden = get_object_or_404(
        Pedido.objects.select_related('cliente', 'mesero', 'mesa').prefetch_related('pagos'), pk=pk)
    return render(request, 'pedidos/orden_detalle.html', {
        'titulo': f'Orden {orden.numero_orden}', 'orden': orden})


@login_required
def orden_editar(request, pk):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, f'Pedido {pedido.numero_orden} actualizado.')
            return redirect('pedidos:orden_lista')
        return render(request, 'pedidos/orden_form.html', {
            'form_orden': form, 'orden_editando': pedido, 'seccion_activa': 'orden-editar'})
    form = PedidoForm(instance=pedido)
    return render(request, 'pedidos/orden_form.html', {
        'form_orden': form, 'orden_editando': pedido, 'seccion_activa': 'orden-editar'})


@login_required
def orden_eliminar(request, pk):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        _eliminar_pedido_con_stock(pedido)
        messages.success(request, '🗑️ Orden eliminada.')
    return redirect('pedidos:orden_lista')


# ── GESTIÓN DE PRODUCTOS ─────────────────────────────────────────────

@login_required
def producto_lista(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    q_prod  = request.GET.get('q_prod', '').strip()
    cat_sel = request.GET.get('categoria', '').strip()
    productos_qs = Producto.objects.select_related('categoria').all()
    if q_prod:
        productos_qs = productos_qs.filter(nombre__icontains=q_prod)
    if cat_sel:
        productos_qs = productos_qs.filter(categoria__id=cat_sel)
    return render(request, 'pedidos/producto_lista.html', {
        'titulo': 'Pedidos', 'productos': productos_qs,
        'categorias': Categoria.objects.all(), 'q_prod': q_prod,
        'cat_sel': cat_sel, 'seccion_activa': 'producto-lista'})


@login_required
def producto_crear(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Producto creado correctamente.')
            return redirect('pedidos:producto_lista')
        messages.error(request, '❌ Corrige los errores en el formulario de producto.')
        return render(request, 'pedidos/producto_form.html', {
            'form_producto': form, 'seccion_activa': 'producto-crear'})
    form = ProductoForm()
    return render(request, 'pedidos/producto_form.html', {
        'form_producto': form, 'seccion_activa': 'producto-crear'})


@login_required
def producto_editar(request, pk):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado correctamente.')
            return redirect('pedidos:producto_lista')
        return render(request, 'pedidos/producto_form.html', {
            'form_producto': form, 'producto_editando': producto,
            'seccion_activa': 'producto-editar'})
    form = ProductoForm(instance=producto)
    return render(request, 'pedidos/producto_form.html', {
        'form_producto': form, 'producto_editando': producto,
        'seccion_activa': 'producto-editar'})


@login_required
def producto_eliminar(request, pk):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, '🗑️ Producto eliminado.')
    return redirect('pedidos:producto_lista')


def _productos_filtrados(request):
    q_prod  = request.GET.get('q_prod', '').strip()
    cat_sel = request.GET.get('categoria', '').strip()
    qs = Producto.objects.select_related('categoria').all()
    if q_prod:
        qs = qs.filter(nombre__icontains=q_prod)
    if cat_sel:
        qs = qs.filter(categoria__id=cat_sel)
    return qs


@login_required
def producto_exportar_pdf(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    productos_qs = _productos_filtrados(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="productos.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = encabezado_reporte("Reporte de Productos")
    data = [['#', 'Nombre', 'Categoría', 'Precio', 'Descripción', 'Disponible']]
    for i, p in enumerate(productos_qs, start=1):
        data.append([f"{i:02d}", p.nombre, p.categoria.nombre if p.categoria else '—',
            f"${p.precio:,.0f}", Paragraph(p.descripcion or '—', styles['Normal']),
            'Sí' if p.disponible else 'No'])
    tabla = Table(data, colWidths=[1.2*cm, 5*cm, 4*cm, 2.5*cm, 8*cm, 2.5*cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#C0392B')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#F5ECD7')),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,0),9),
        ('FONTSIZE',(0,1),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#FDF7EC'),colors.HexColor('#EDE3C8')]),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#D4C4A0')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'), ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5), ('LEFTPADDING',(0,0),(-1,-1),5),
        ('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))
    elements.append(tabla)
    doc.build(elements)
    return response


@login_required
def producto_exportar_excel(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    productos_qs = _productos_filtrados(request)
    filas = []
    for i, p in enumerate(productos_qs, start=1):
        filas.append([f"{i:02d}", p.nombre, p.categoria.nombre if p.categoria else '—',
            p.precio, p.descripcion or '—', 'Sí' if p.disponible else 'No'])
    return _respuesta_excel("Reporte de Productos", "productos.xlsx",
        ['#', 'Nombre', 'Categoría', 'Precio', 'Descripción', 'Disponible'],
        filas, [6, 28, 22, 14, 50, 12], cols_dinero=(3,))


# ── INVENTARIO DE BEBIDAS ────────────────────────────────────────────

@login_required
def inventario_lista(request):
    """Lista de bebidas con su stock, buscador, filtro por estado y paginación."""
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    q_inv      = request.GET.get('q_inv', '').strip()
    estado_inv = request.GET.get('estado_inv', '').strip()

    base = _bebidas()

    # Resumen (tarjetas de arriba): siempre sobre todas las bebidas, sin filtros
    resumen = {
        'total':          base.count(),
        'agotadas':       base.filter(stock_actual__lte=0).count(),
        'bajas':          base.filter(stock_actual__gt=0, stock_actual__lte=F('stock_minimo')).count(),
        'sin_configurar': base.filter(stock_actual__isnull=True).count(),
    }

    bebidas_qs = base.order_by('nombre')
    if q_inv:
        bebidas_qs = bebidas_qs.filter(nombre__icontains=q_inv)
    if estado_inv == 'agotadas':
        bebidas_qs = bebidas_qs.filter(stock_actual__lte=0)
    elif estado_inv == 'bajas':
        bebidas_qs = bebidas_qs.filter(stock_actual__gt=0, stock_actual__lte=F('stock_minimo'))
    elif estado_inv == 'sin_configurar':
        bebidas_qs = bebidas_qs.filter(stock_actual__isnull=True)

    paginator = Paginator(bebidas_qs, 10)  # 10 bebidas por página
    page_obj  = paginator.get_page(request.GET.get('page'))

    # El estado de cada bebida (b.estado_stock) lo calcula la propiedad del modelo Producto

    return render(request, 'pedidos/inventario_lista.html', {
        'titulo': 'Pedidos',
        'bebidas': page_obj,            # la plantilla itera sobre "bebidas"
        'page_obj': page_obj,
        'paginas': _rango_paginas(page_obj),
        'querystring': _querystring_sin_page(request),
        'resumen': resumen,
        'q_inv': q_inv,
        'estado_inv': estado_inv,
        'seccion_activa': 'inventario-lista'})


@login_required
def inventario_reabastecer(request, pk):
    """Suma al stock las unidades que llegaron del proveedor."""
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    destino = _destino_seguro(request, 'pedidos:inventario_lista')
    if request.method != 'POST':
        return redirect(destino)

    try:
        cantidad = int(request.POST.get('cantidad', '').strip())
    except ValueError:
        messages.error(request, '❌ Escribe una cantidad válida (número entero).')
        return redirect(destino)
    if not 1 <= cantidad <= LIMITE_STOCK:
        messages.error(request, f'❌ La cantidad debe estar entre 1 y {LIMITE_STOCK}.')
        return redirect(destino)

    with transaction.atomic():
        bebida = get_object_or_404(_bebidas().select_for_update(), pk=pk)
        # Si no tenía stock configurado, empieza a controlarse desde 0 + lo que llegó
        bebida.stock_actual = (bebida.stock_actual or 0) + cantidad
        if bebida.stock_actual > LIMITE_STOCK:
            messages.error(request, f'❌ El stock no puede pasar de {LIMITE_STOCK} unidades.')
            return redirect(destino)
        bebida.save(update_fields=['stock_actual'])

    messages.success(
        request,
        f'✅ Se agregaron {cantidad} unidades a "{bebida.nombre}". Stock actual: {bebida.stock_actual}.')
    return redirect(destino)


@login_required
def inventario_ajustar(request, pk):
    """Corrige el stock y el mínimo (después de contar, o para configurarlo por primera vez)."""
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    destino = _destino_seguro(request, 'pedidos:inventario_lista')
    if request.method != 'POST':
        return redirect(destino)

    stock_raw  = request.POST.get('stock_actual', '').strip()
    minimo_raw = request.POST.get('stock_minimo', '').strip()
    try:
        stock_minimo = int(minimo_raw)
        stock_actual = int(stock_raw) if stock_raw != '' else None   # vacío = no se controla
    except ValueError:
        messages.error(request, '❌ El stock y el mínimo deben ser números enteros.')
        return redirect(destino)

    if not 0 <= stock_minimo <= LIMITE_STOCK:
        messages.error(request, f'❌ El mínimo debe estar entre 0 y {LIMITE_STOCK}.')
        return redirect(destino)
    if stock_actual is not None and not 0 <= stock_actual <= LIMITE_STOCK:
        messages.error(request, f'❌ El stock debe estar entre 0 y {LIMITE_STOCK}.')
        return redirect(destino)

    with transaction.atomic():
        bebida = get_object_or_404(_bebidas().select_for_update(), pk=pk)
        bebida.stock_actual = stock_actual
        bebida.stock_minimo = stock_minimo
        bebida.save(update_fields=['stock_actual', 'stock_minimo'])

    if stock_actual is None:
        messages.success(
            request,
            f'✅ Mínimo de "{bebida.nombre}" guardado en {stock_minimo}. '
            f'Aún no tiene stock configurado, así que se vende sin límite.')
    else:
        messages.success(request, f'✅ Inventario de "{bebida.nombre}" actualizado: {stock_actual} unidades.')
    return redirect(destino)


# ── GESTIÓN DE CATEGORÍAS ──────────────────────────────────────────

@login_required
def categoria_lista(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    q_cat = request.GET.get('q_cat', '').strip()
    categorias_qs = Categoria.objects.all()
    if q_cat:
        categorias_qs = categorias_qs.filter(nombre__icontains=q_cat)
    return render(request, 'pedidos/categoria_lista.html', {
        'titulo': 'Pedidos', 'categorias': categorias_qs,
        'q_cat': q_cat, 'seccion_activa': 'categoria-lista'})


@login_required
def categoria_crear(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Categoría creada correctamente.')
            return redirect('pedidos:categoria_lista')
        messages.error(request, '❌ Corrige los errores en el formulario.')
        return render(request, 'pedidos/categoria_form.html', {
            'form_categoria': form, 'seccion_activa': 'categoria-crear'})
    form = CategoriaForm()
    return render(request, 'pedidos/categoria_form.html', {
        'form_categoria': form, 'seccion_activa': 'categoria-crear'})


@login_required
def categoria_editar(request, pk):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Categoría actualizada correctamente.')
            return redirect('pedidos:categoria_lista')
        return render(request, 'pedidos/categoria_form.html', {
            'form_categoria': form, 'categoria_editando': categoria,
            'seccion_activa': 'categoria-editar'})
    form = CategoriaForm(instance=categoria)
    return render(request, 'pedidos/categoria_form.html', {
        'form_categoria': form, 'categoria_editando': categoria,
        'seccion_activa': 'categoria-editar'})


@login_required
def categoria_eliminar(request, pk):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, '🗑️ Categoría eliminada.')
    return redirect('pedidos:categoria_lista')


def _categorias_filtradas(request):
    q_cat = request.GET.get('q_cat', '').strip()
    qs = Categoria.objects.all()
    if q_cat:
        qs = qs.filter(nombre__icontains=q_cat)
    return qs


@login_required
def categoria_exportar_pdf(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    categorias_qs = _categorias_filtradas(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="categorias.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = encabezado_reporte("Reporte de Categorías")
    data = [['#', 'Nombre', 'Descripción']]
    for i, c in enumerate(categorias_qs, start=1):
        data.append([f"{i:02d}", c.nombre, Paragraph(c.descripcion or '—', styles['Normal'])])
    tabla = Table(data, colWidths=[1.2*cm, 5*cm, 14*cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#C0392B')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#F5ECD7')),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,0),9),
        ('FONTSIZE',(0,1),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#FDF7EC'),colors.HexColor('#EDE3C8')]),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#D4C4A0')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'), ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5), ('LEFTPADDING',(0,0),(-1,-1),5),
        ('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))
    elements.append(tabla)
    doc.build(elements)
    return response


@login_required
def categoria_exportar_excel(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    categorias_qs = _categorias_filtradas(request)
    filas = [[f"{i:02d}", c.nombre, c.descripcion or '—']
             for i, c in enumerate(categorias_qs, start=1)]
    return _respuesta_excel("Reporte de Categorías", "categorias.xlsx",
        ['#', 'Nombre', 'Descripción'], filas, [6, 28, 60])


# ── GESTIÓN DE CLIENTES ─────────────────────────────────────────────

@login_required
def cliente_lista(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    q_cli = request.GET.get('q_cli', '').strip()
    clientes_qs = Cliente.objects.all()
    if q_cli:
        clientes_qs = clientes_qs.filter(
            Q(nombre_completo__icontains=q_cli) | Q(documento__icontains=q_cli))
    return render(request, 'pedidos/cliente_lista.html', {
        'titulo': 'Pedidos', 'clientes': clientes_qs,
        'q_cli': q_cli, 'seccion_activa': 'cliente-lista'})


@login_required
def cliente_crear(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cliente registrado correctamente.')
            return redirect('pedidos:cliente_lista')
        messages.error(request, '❌ Corrige los errores en el formulario.')
        return render(request, 'pedidos/cliente_form.html', {
            'form_cliente': form, 'seccion_activa': 'cliente-crear'})
    form = ClienteForm()
    return render(request, 'pedidos/cliente_form.html', {
        'form_cliente': form, 'seccion_activa': 'cliente-crear'})


@login_required
def cliente_editar(request, pk):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente actualizado correctamente.')
            return redirect('pedidos:cliente_lista')
        return render(request, 'pedidos/cliente_form.html', {
            'form_cliente': form, 'cliente_editando': cliente,
            'seccion_activa': 'cliente-editar'})
    form = ClienteForm(instance=cliente)
    return render(request, 'pedidos/cliente_form.html', {
        'form_cliente': form, 'cliente_editando': cliente,
        'seccion_activa': 'cliente-editar'})


@login_required
def cliente_eliminar(request, pk):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, '🗑️ Cliente eliminado.')
    return redirect('pedidos:cliente_lista')


def _clientes_filtrados(request):
    q_cli = request.GET.get('q_cli', '').strip()
    qs = Cliente.objects.all()
    if q_cli:
        qs = qs.filter(Q(nombre_completo__icontains=q_cli) | Q(documento__icontains=q_cli))
    return qs


@login_required
def cliente_exportar_pdf(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    clientes_qs = _clientes_filtrados(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="clientes.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = encabezado_reporte("Reporte de Clientes")
    data = [['#', 'Nombre Completo', 'Teléfono', 'Documento', 'Dirección']]
    for i, c in enumerate(clientes_qs, start=1):
        data.append([f"{i:02d}", c.nombre_completo, c.telefono or '—',
            f"{c.tipo_documento} {c.documento}", Paragraph(c.direccion or '—', styles['Normal'])])
    tabla = Table(data, colWidths=[1.2*cm, 5*cm, 3.5*cm, 4*cm, 9*cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#C0392B')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#F5ECD7')),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,0),9),
        ('FONTSIZE',(0,1),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#FDF7EC'),colors.HexColor('#EDE3C8')]),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#D4C4A0')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'), ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5), ('LEFTPADDING',(0,0),(-1,-1),5),
        ('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))
    elements.append(tabla)
    doc.build(elements)
    return response


@login_required
def cliente_exportar_excel(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    clientes_qs = _clientes_filtrados(request)
    filas = [[f"{i:02d}", c.nombre_completo, c.telefono or '—',
              c.tipo_documento, c.documento, c.direccion or '—']
             for i, c in enumerate(clientes_qs, start=1)]
    return _respuesta_excel("Reporte de Clientes", "clientes.xlsx",
        ['#', 'Nombre Completo', 'Teléfono', 'Tipo Documento', 'Documento', 'Dirección'],
        filas, [6, 30, 16, 16, 18, 45])


# ── EXPORTACIÓN DE ÓRDENES ───────────────────────────────────────────

def _ordenes_filtradas(request):
    q_orden = request.GET.get('q_orden', '').strip()
    filtro = _resolver_filtro_fecha(request)
    qs = (Pedido.objects.select_related('cliente', 'mesero', 'mesa')
        .prefetch_related('items__producto').order_by('-fecha_creacion'))
    if q_orden:
        clean_q = q_orden.replace('ORD-', '').lstrip('0')
        if clean_q.isdigit():
            qs = qs.filter(Q(id=int(clean_q)) | Q(cliente__nombre_completo__icontains=q_orden))
        else:
            qs = qs.filter(cliente__nombre_completo__icontains=q_orden)
    if filtro['efectivo_desde']:
        qs = qs.filter(fecha_creacion__date__gte=filtro['efectivo_desde'])
    if filtro['efectivo_hasta']:
        qs = qs.filter(fecha_creacion__date__lte=filtro['efectivo_hasta'])
    return qs


@login_required
def orden_exportar_pdf(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    ordenes_qs = _ordenes_filtradas(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="ordenes.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = encabezado_reporte("Reporte de Órdenes Comerciales")
    data = [['Número', 'Cliente', 'Mesa', 'Productos', 'Estado', 'Subtotal', 'Impuesto', 'Total', 'Fecha']]
    for o in ordenes_qs:
        productos_str = ', '.join(f"{it.cantidad}x {it.producto.nombre}" for it in o.items.all()) or '—'
        data.append([o.numero_orden, str(o.cliente), str(o.mesa) if o.mesa else '—',
            Paragraph(productos_str, styles['Normal']), o.get_estado_display(),
            f"${o.subtotal:,.0f}", f"${o.impuesto:,.0f}", f"${o.total:,.0f}",
            o.fecha_creacion.strftime('%d/%m/%Y %H:%M')])
    tabla = Table(data, colWidths=[2.2*cm,3.5*cm,2*cm,6*cm,2.5*cm,2.2*cm,2.2*cm,2.2*cm,3.5*cm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#C0392B')),
        ('TEXTCOLOR',(0,0),(-1,0),colors.HexColor('#F5ECD7')),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'), ('FONTSIZE',(0,0),(-1,0),9),
        ('FONTSIZE',(0,1),(-1,-1),8),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#FDF7EC'),colors.HexColor('#EDE3C8')]),
        ('GRID',(0,0),(-1,-1),0.5,colors.HexColor('#D4C4A0')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'), ('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5), ('LEFTPADDING',(0,0),(-1,-1),5),
        ('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))
    elements.append(tabla)
    doc.build(elements)
    return response


@login_required
def orden_exportar_excel(request):
    if _es_cajero(request) or _es_mesero(request) or _es_cocinera(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    ordenes_qs = _ordenes_filtradas(request)
    filas = []
    for o in ordenes_qs:
        productos_str = ', '.join(f"{it.cantidad}x {it.producto.nombre}" for it in o.items.all()) or '—'
        filas.append([o.numero_orden, str(o.cliente), str(o.mesa) if o.mesa else '—',
            productos_str, o.get_estado_display(), o.subtotal, o.impuesto, o.total,
            o.fecha_creacion.strftime('%d/%m/%Y %H:%M')])
    return _respuesta_excel("Reporte de Órdenes Comerciales", "ordenes.xlsx",
        ['Número', 'Cliente', 'Mesa', 'Productos', 'Estado', 'Subtotal', 'Impuesto', 'Total', 'Fecha'],
        filas, [12, 24, 12, 45, 16, 14, 14, 14, 18], cols_dinero=(5, 6, 7))
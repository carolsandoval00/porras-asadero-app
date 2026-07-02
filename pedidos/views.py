import csv
import json
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from usuarios.models import Cliente

from .forms import CategoriaForm, ClienteForm, PedidoForm, ProductoForm
from .models import Categoria, Pedido, PedidoItem, Producto

# ── ReportLab (PDF) ─────────────────────────────────────────────────
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# ── HELPERS PRIVADOS ────────────────────────────────────────────────

def _productos_disponibles():
    """Obtiene los productos actualmente disponibles para pedir.

    Returns:
        QuerySet[Producto]: Productos con ``disponible=True``, con su
            categoría precargada (``select_related``) y ordenados por
            nombre de categoría y luego por nombre de producto.
    """
    return (
        Producto.objects
        .filter(disponible=True)
        .select_related('categoria')
        .order_by('categoria__nombre', 'nombre')
    )


def _parse_items_from_post(request):
    """Extrae la lista de ítems (producto + cantidad) de un POST dinámico.

    El formulario del frontend envía los ítems como campos indexados
    ``items[0][id]``, ``items[0][cantidad]``, ``items[1][id]``, etc.
    Esta función itera esos índices hasta encontrar uno vacío y arma
    la lista de ítems válidos.

    Ítems inválidos se descartan silenciosamente:
        - Si el producto no existe o no está disponible
          (``Producto.DoesNotExist``).
        - Si la cantidad no es un entero válido (``ValueError``).
        - Si la cantidad es menor o igual a 0.

    Args:
        request (HttpRequest): Petición POST cuyo body de formulario
            contiene los campos ``items[i][id]`` e ``items[i][cantidad]``
            para ``i`` = 0, 1, 2, ...

    Returns:
        list[dict]: Lista de diccionarios con la forma
            ``{'producto': Producto, 'cantidad': int}``, uno por cada
            ítem válido encontrado. Puede ser una lista vacía si no se
            envió ningún ítem válido.
    """
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
    """Serializa los ítems de un pedido a JSON para precargar el formulario.

    Usado al editar un pedido: el frontend necesita conocer los
    productos y cantidades ya guardados para reconstruir la interfaz
    de selección de ítems en JavaScript.

    Args:
        pedido (Pedido): Instancia del pedido cuyos ítems se quieren
            serializar.

    Returns:
        str: Cadena JSON representando una lista de objetos con las
            claves ``id`` (str, PK del producto), ``nombre`` (str),
            ``precio`` (int) y ``cantidad`` (int).
    """
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


def _pedidos_filtrados(request):
    """Obtiene los pedidos aplicando los filtros de búsqueda y estado.

    Args:
        request (HttpRequest): Petición cuyos parámetros GET pueden
            incluir:
                q (str, opcional): Texto a buscar en el nombre del
                    cliente o en la descripción del pedido
                    (coincidencia parcial, insensible a mayúsculas).
                estado (str, opcional): Valor exacto de ``estado`` por
                    el cual filtrar (debe coincidir con alguno de
                    ``Pedido.ESTADO_CHOICES``).

    Returns:
        QuerySet[Pedido]: Pedidos que cumplen los filtros dados, con
            ``cliente``, ``mesero`` y ``mesa`` precargados
            (``select_related``) y sus ``items__producto`` precargados
            (``prefetch_related``). Ordenados de forma ASCENDENTE por
            ``fecha_creacion`` (así el PED-00001 siempre aparece
            primero).
    """
    q = request.GET.get('q', '').strip()
    estado_sel = request.GET.get('estado', '').strip()

    qs = (
        Pedido.objects
        .select_related('cliente', 'mesero', 'mesa')
        .prefetch_related('items__producto')
        .order_by('fecha_creacion')
    )
    if q:
        qs = qs.filter(
            Q(cliente__nombre_completo__icontains=q) | Q(descripcion__icontains=q)
        )
    if estado_sel:
        qs = qs.filter(estado=estado_sel)
    return qs


# ── TABLERO PRINCIPAL (DASHBOARD) ──────────────────────────────────

@login_required
def dashboard(request):
    """Muestra el tablero principal del módulo de pedidos.

    Calcula los totales generales (pedidos, productos, categorías,
    clientes) y arma la lista de los 5 pedidos más recientes en
    orden ascendente (el más reciente al final).

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.

    Returns:
        HttpResponse: Renderiza ``pedidos/dashboard.html`` con el
            contexto:
                total_pedidos (int): Cantidad total de pedidos.
                pedidos_pendientes (int): Pedidos con estado
                    ``'PREPARACION'``.
                total_productos (int): Cantidad total de productos.
                total_categorias (int): Cantidad total de categorías.
                total_clientes (int): Cantidad total de clientes.
                ultimos_pedidos (list[Pedido]): Los 5 pedidos más
                    recientes, en orden ascendente por fecha.
    """
    total_pedidos      = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado='PREPARACION').count()
    total_productos    = Producto.objects.count()
    total_categorias   = Categoria.objects.count()
    total_clientes     = Cliente.objects.count()

    # Se toman los 5 pedidos más recientes (orden descendente por fecha)
    # y luego se invierte la lista para mostrarlos en orden ascendente por #.
    ultimos_pedidos = list(
        Pedido.objects
        .select_related('cliente', 'mesero', 'mesa')
        .order_by('-fecha_creacion')[:5]
    )[::-1]

    context = { 'titulo': 'Módulo de Pedidos', 'total_pedidos': total_pedidos, 'pedidos_pendientes': pedidos_pendientes, 'total_ordenes': total_pedidos, 'total_productos': total_productos, 'total_categorias': total_categorias, 'total_clientes': total_clientes, 'ultimos_pedidos': ultimos_pedidos, }
    return render(request, 'pedidos/dashboard.html', context)


# ── GESTIÓN DE PEDIDOS ───────────────────────────────────────────────

@login_required
def pedido_lista(request):
    """Lista los pedidos filtrados, agrupados por fecha de creación.

    Aplica los mismos filtros que ``_pedidos_filtrados`` y luego
    agrupa el resultado por día usando ``itertools.groupby`` (por eso
    el queryset debe venir ordenado por fecha antes de agrupar).

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta los parámetros opcionales ``q`` y ``estado``
            descritos en ``_pedidos_filtrados``.

    Returns:
        HttpResponse: Renderiza ``pedidos/pedido_lista.html`` con el
            contexto:
                pedidos_por_fecha (list[dict]): Lista de grupos con la
                    forma ``{'fecha': date, 'pedidos': list[Pedido],
                    'count': int}``, uno por cada día distinto.
                estados (tuple): Opciones de ``Pedido.ESTADO_CHOICES``.
                q (str): Valor del filtro de búsqueda aplicado.
                estado_sel (str): Valor del filtro de estado aplicado.
    """
    q         = request.GET.get('q', '').strip()
    estado_sel = request.GET.get('estado', '').strip()

    pedidos_qs = _pedidos_filtrados(request)

    pedidos_lista_data = list(pedidos_qs)
    pedidos_por_fecha  = []
    for fecha, grupo in groupby(pedidos_lista_data, key=lambda p: p.fecha_creacion.date()):
        items = list(grupo)
        pedidos_por_fecha.append({'fecha': fecha, 'pedidos': items, 'count': len(items)})

    context = { 'titulo': 'Módulo de Pedidos', 'pedidos_por_fecha': pedidos_por_fecha, 'estados': Pedido.ESTADO_CHOICES, 'q': q, 'estado_sel': estado_sel, 'seccion_activa': 'pedido-lista', }
    return render(request, 'pedidos/pedido_lista.html', context)


@login_required
def pedido_exportar_pdf(request):
    """Exporta los pedidos filtrados a un archivo PDF descargable.

    Usa ReportLab para construir una tabla en orientación horizontal
    (landscape A4) con una fila por pedido, incluyendo sus productos
    concatenados en una sola celda.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta los mismos parámetros de filtro que
            ``_pedidos_filtrados`` (``q``, ``estado``).

    Returns:
        HttpResponse: Documento PDF (``content_type='application/pdf'``)
            con cabecera ``Content-Disposition: attachment;
            filename="pedidos.pdf"``, listo para descarga directa.
    """
    pedidos_qs = _pedidos_filtrados(request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="pedidos.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=1 * cm, rightMargin=1 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles   = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Reporte de Pedidos", styles['Title']))
    elements.append(Spacer(1, 0.5 * cm))

    # Cabecera
    data = [['#', 'Cliente', 'Mesa', 'Productos', 'Estado', 'Total', 'Fecha']]

    for p in pedidos_qs:
        productos_str = ', '.join(
            f"{it.cantidad}x {it.producto.nombre}" for it in p.items.all()
        ) or '—'
        data.append([
            p.numero_pedido,
            str(p.cliente),
            str(p.mesa) if p.mesa else '—',
            Paragraph(productos_str, styles['Normal']),
            p.get_estado_display(),
            f"${p.total:,.0f}",
            p.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
        ])

    tabla = Table(
        data,
        colWidths=[1.8*cm, 4*cm, 2.5*cm, 7.5*cm, 3*cm, 2.5*cm, 4*cm],
        repeatRows=1,
    )
    tabla.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#C0392B')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.HexColor('#F5ECD7')),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 9),
        # Filas
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#FDF7EC'), colors.HexColor('#EDE3C8')]),
        # Bordes y padding
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#D4C4A0')),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
    ]))

    elements.append(tabla)
    doc.build(elements)
    return response


@login_required
def pedido_exportar_excel(request):
    """Exporta los pedidos filtrados a un archivo CSV (compatible con Excel).

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta los mismos parámetros de filtro que
            ``_pedidos_filtrados`` (``q``, ``estado``).

    Returns:
        HttpResponse: Archivo CSV (``content_type='text/csv;
            charset=utf-8-sig'``) con cabecera
            ``Content-Disposition: attachment; filename="pedidos.csv"``,
            listo para descarga directa. El BOM UTF-8 (``utf-8-sig``)
            asegura que Excel muestre correctamente los acentos y la ñ.
    """
    pedidos_qs = _pedidos_filtrados(request)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="pedidos.csv"'

    writer = csv.writer(response)
    writer.writerow(['#', 'Cliente', 'Mesa', 'Productos', 'Descripción', 'Estado', 'Total', 'Fecha'])

    for p in pedidos_qs:
        productos_str = ', '.join(
            f"{it.cantidad}x {it.producto.nombre}" for it in p.items.all()
        ) or '—'
        writer.writerow([
            p.numero_pedido,
            str(p.cliente),
            str(p.mesa) if p.mesa else '—',
            productos_str,
            p.descripcion or '—',
            p.get_estado_display(),
            p.total,
            p.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
        ])

    return response


@login_required
def pedido_crear(request):
    """Muestra y procesa el formulario de creación de un pedido nuevo.

    En GET, muestra el formulario junto con los productos disponibles
    para seleccionar. En POST, valida el formulario y los ítems
    enviados dinámicamente (ver ``_parse_items_from_post``), calcula
    el total sumando ``precio * cantidad`` de cada ítem, guarda el
    pedido con estado inicial ``'PREPARACION'`` y crea los
    ``PedidoItem`` asociados en bloque.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado. En POST debe incluir los campos del
            ``PedidoForm`` más los campos dinámicos ``items[i][id]``
            e ``items[i][cantidad]``.

    Returns:
        HttpResponse: En GET, o en POST con errores (formulario
            inválido o sin ítems), renderiza
            ``pedidos/pedido_form.html`` con el formulario y los
            productos disponibles.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``pedidos:pedido_lista`` con un mensaje de éxito.
    """
    productos_disponibles = _productos_disponibles()

    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.mesero       = request.user
            pedido.fecha_creacion = timezone.now()
            pedido.estado       = 'PREPARACION'

            items_data = _parse_items_from_post(request)
            if not items_data:
                messages.error(request, '❌ Agrega al menos un producto al pedido.')
                context = { 'form': form, 'productos_disponibles': productos_disponibles, 'seccion_activa': 'pedido-crear', }
                return render(request, 'pedidos/pedido_form.html', context)

            total          = sum(it['producto'].precio * it['cantidad'] for it in items_data)
            pedido.total   = total
            pedido.subtotal = total
            pedido.impuestos = 0
            pedido.save()

            PedidoItem.objects.bulk_create([
                PedidoItem(
                    pedido=pedido,
                    producto=it['producto'],
                    cantidad=it['cantidad'],
                    precio_unitario=it['producto'].precio,
                )
                for it in items_data
            ])

            messages.success(request, f'✅ Pedido {pedido.numero_pedido} creado correctamente.')
            return redirect('pedidos:pedido_lista')

        messages.error(request, '❌ Corrige los errores en el formulario de pedido.')
        context = { 'form': form, 'productos_disponibles': productos_disponibles, 'seccion_activa': 'pedido-crear', }
        return render(request, 'pedidos/pedido_form.html', context)

    form = PedidoForm()
    context = { 'form': form, 'productos_disponibles': productos_disponibles, 'seccion_activa': 'pedido-crear', }
    return render(request, 'pedidos/pedido_form.html', context)


@login_required
def pedido_editar(request, pk):
    """Muestra y procesa el formulario de edición de un pedido existente.

    En GET, precarga el formulario y serializa los ítems actuales a
    JSON (ver ``_items_as_json``) para que el frontend reconstruya la
    lista de productos seleccionados. En POST, si se enviaron ítems
    nuevos, reemplaza por completo los ``PedidoItem`` existentes
    (borra todos y vuelve a crearlos) y recalcula el total; si no se
    envió ningún ítem, solo actualiza los demás campos del formulario.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado. En POST debe incluir los campos del
            ``PedidoForm`` y, opcionalmente, los campos dinámicos
            ``items[i][id]`` e ``items[i][cantidad]``.
        pk (int): Clave primaria del pedido a editar.

    Returns:
        HttpResponse: En GET, o en POST con errores de formulario,
            renderiza ``pedidos/pedido_form.html`` con el formulario,
            el pedido, sus ítems en JSON y los productos disponibles.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``pedidos:pedido_lista`` con un mensaje de éxito.

    Raises:
        Http404: Si no existe ningún pedido con esa ``pk`` (lanzado
            por ``get_object_or_404``).
    """
    pedido                = get_object_or_404(Pedido, pk=pk)
    productos_disponibles = _productos_disponibles()

    if request.method == 'POST':
        items_data = _parse_items_from_post(request)
        form       = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            p = form.save(commit=False)
            if items_data:
                total      = sum(it['producto'].precio * it['cantidad'] for it in items_data)
                p.total    = total
                p.subtotal = total
                p.save()
                pedido.items.all().delete()
                PedidoItem.objects.bulk_create([
                    PedidoItem(
                        pedido=pedido,
                        producto=it['producto'],
                        cantidad=it['cantidad'],
                        precio_unitario=it['producto'].precio,
                    )
                    for it in items_data
                ])
            else:
                p.save()
            messages.success(request, ' Pedido actualizado correctamente.')
            return redirect('pedidos:pedido_lista')

        context = { 'form': form, 'pedido': pedido, 'pedido_items_json': _items_as_json(pedido), 'productos_disponibles': productos_disponibles, 'seccion_activa': 'pedido-editar', }
        return render(request, 'pedidos/pedido_form.html', context)

    form = PedidoForm(instance=pedido)
    context = { 'form': form, 'pedido': pedido, 'pedido_items_json': _items_as_json(pedido), 'productos_disponibles': productos_disponibles, 'seccion_activa': 'pedido-editar', }
    return render(request, 'pedidos/pedido_form.html', context)


@login_required
def pedido_eliminar(request, pk):
    """Elimina un pedido existente.

    Solo elimina en una petición POST; en GET simplemente redirige
    sin hacer cambios (comportamiento típico para vistas invocadas
    desde un botón/formulario de confirmación).

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado.
        pk (int): Clave primaria del pedido a eliminar.

    Returns:
        HttpResponseRedirect: Redirige a ``pedidos:pedido_lista``. Si
            la petición fue POST, incluye un mensaje de éxito.

    Raises:
        Http404: Si no existe ningún pedido con esa ``pk`` (lanzado
            por ``get_object_or_404``).
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Pedido eliminado.')
    return redirect('pedidos:pedido_lista')


# ── GESTIÓN DE ÓRDENES (FACTURACIÓN) ──────────────────────────────────

@login_required
def orden_lista(request):
    """Lista las órdenes (pedidos) filtradas y agrupadas por fecha.

    A diferencia de ``pedido_lista``, la búsqueda por texto acepta
    tanto el ID numérico de la orden (con o sin el prefijo
    ``'ORD-'`` y ceros a la izquierda) como el nombre del cliente.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta el parámetro opcional ``q_orden`` (str): término de
            búsqueda por ID de orden o nombre de cliente.

    Returns:
        HttpResponse: Renderiza ``pedidos/orden_lista.html`` con el
            contexto:
                ordenes_por_fecha (list[dict]): Grupos con la forma
                    ``{'fecha': date, 'ordenes': list[Pedido],
                    'count': int}``.
                q_orden (str): Valor del filtro de búsqueda aplicado.
    """
    q_orden = request.GET.get('q_orden', '').strip()

    ordenes_qs = (
        Pedido.objects
        .select_related('cliente', 'mesero', 'mesa')
        .order_by('fecha_creacion')
    )
    if q_orden:
        clean_q = q_orden.replace('ORD-', '').lstrip('0')
        if clean_q.isdigit():
            ordenes_qs = ordenes_qs.filter(
                Q(id=int(clean_q)) | Q(cliente__nombre_completo__icontains=q_orden)
            )
        else:
            ordenes_qs = ordenes_qs.filter(cliente__nombre_completo__icontains=q_orden)

    ordenes_lista_data = list(ordenes_qs)
    ordenes_por_fecha  = []
    for fecha, grupo in groupby(ordenes_lista_data, key=lambda o: o.fecha_creacion.date()):
        items = list(grupo)
        ordenes_por_fecha.append({'fecha': fecha, 'ordenes': items, 'count': len(items)})

    context = { 'titulo': 'Módulo de Pedidos', 'ordenes_por_fecha': ordenes_por_fecha, 'q_orden': q_orden, 'seccion_activa': 'orden-lista', }
    return render(request, 'pedidos/orden_lista.html', context)


@login_required
def orden_detalle(request, pk):
    """Muestra el detalle completo de una orden, incluyendo sus pagos.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
        pk (int): Clave primaria de la orden (``Pedido``) a mostrar.

    Returns:
        HttpResponse: Renderiza ``pedidos/orden_detalle.html`` con el
            contexto ``{'titulo': str, 'orden': Pedido}``, donde
            ``orden`` trae precargados ``cliente``, ``mesero``,
            ``mesa`` (``select_related``) y ``pagos``
            (``prefetch_related``).

    Raises:
        Http404: Si no existe ninguna orden con esa ``pk`` (lanzado
            por ``get_object_or_404``).
    """
    orden = get_object_or_404(
        Pedido.objects.select_related('cliente', 'mesero', 'mesa').prefetch_related('pagos'),
        pk=pk,
    )
    context = {
        'titulo': f'Orden {orden.numero_orden}',
        'orden': orden,
    }
    return render(request, 'pedidos/orden_detalle.html', context)


@login_required
def orden_editar(request, pk):
    """Muestra y procesa el formulario de edición de una orden.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado. En POST debe incluir los campos del
            ``PedidoForm``.
        pk (int): Clave primaria de la orden (``Pedido``) a editar.

    Returns:
        HttpResponse: En GET, o en POST con errores de formulario,
            renderiza ``pedidos/orden_form.html`` con el formulario y
            la orden en edición.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``pedidos:orden_lista`` con un mensaje de éxito.

    Raises:
        Http404: Si no existe ninguna orden con esa ``pk`` (lanzado
            por ``get_object_or_404``).
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        form = PedidoForm(request.POST, instance=pedido)
        if form.is_valid():
            form.save()
            messages.success(request, f' Pedido {pedido.numero_orden} actualizado.')
            return redirect('pedidos:orden_lista')
        context = { 'form_orden': form, 'orden_editando': pedido, 'seccion_activa': 'orden-editar', }
        return render(request, 'pedidos/orden_form.html', context)

    form = PedidoForm(instance=pedido)
    context = { 'form_orden': form, 'orden_editando': pedido, 'seccion_activa': 'orden-editar', }
    return render(request, 'pedidos/orden_form.html', context)


@login_required
def orden_eliminar(request, pk):
    """Elimina una orden existente.

    Solo elimina en una petición POST; en GET redirige sin cambios.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado.
        pk (int): Clave primaria de la orden (``Pedido``) a eliminar.

    Returns:
        HttpResponseRedirect: Redirige a ``pedidos:orden_lista``. Si
            la petición fue POST, incluye un mensaje de éxito.

    Raises:
        Http404: Si no existe ninguna orden con esa ``pk`` (lanzado
            por ``get_object_or_404``).
    """
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Orden eliminada.')
    return redirect('pedidos:orden_lista')


# ── GESTIÓN DE PRODUCTOS ─────────────────────────────────────────────

@login_required
def producto_lista(request):
    """Lista los productos, con filtro opcional por nombre y categoría.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta los parámetros opcionales:
                q_prod (str): Texto a buscar en el nombre del producto.
                categoria (str): ID de categoría por la cual filtrar.

    Returns:
        HttpResponse: Renderiza ``pedidos/producto_lista.html`` con el
            contexto:
                productos (QuerySet[Producto]): Productos filtrados,
                    con su categoría precargada.
                categorias (QuerySet[Categoria]): Todas las categorías
                    (para el selector de filtro).
                q_prod (str): Valor del filtro de texto aplicado.
                cat_sel (str): Valor del filtro de categoría aplicado.
    """
    q_prod  = request.GET.get('q_prod', '').strip()
    cat_sel = request.GET.get('categoria', '').strip()

    productos_qs = Producto.objects.select_related('categoria').all()
    if q_prod:
        productos_qs = productos_qs.filter(nombre__icontains=q_prod)
    if cat_sel:
        productos_qs = productos_qs.filter(categoria__id=cat_sel)

    context = { 'titulo': 'Módulo de Pedidos', 'productos': productos_qs, 'categorias': Categoria.objects.all(), 'q_prod': q_prod, 'cat_sel': cat_sel, 'seccion_activa': 'producto-lista', }
    return render(request, 'pedidos/producto_lista.html', context)


@login_required
def producto_crear(request):
    """Muestra y procesa el formulario de creación de un producto.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado. En POST debe incluir los campos del
            ``ProductoForm``.

    Returns:
        HttpResponse: En GET, o en POST con errores de formulario,
            renderiza ``pedidos/producto_form.html``.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``pedidos:producto_lista`` con un mensaje de éxito.
    """
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Producto creado correctamente.')
            return redirect('pedidos:producto_lista')
        messages.error(request, '❌ Corrige los errores en el formulario de producto.')
        context = { 'form_producto': form, 'seccion_activa': 'producto-crear', }
        return render(request, 'pedidos/producto_form.html', context)

    form = ProductoForm()
    context = { 'form_producto': form, 'seccion_activa': 'producto-crear', }
    return render(request, 'pedidos/producto_form.html', context)


@login_required
def producto_editar(request, pk):
    """Muestra y procesa el formulario de edición de un producto.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado. En POST debe incluir los campos del
            ``ProductoForm``.
        pk (int): Clave primaria del producto a editar.

    Returns:
        HttpResponse: En GET, o en POST con errores de formulario,
            renderiza ``pedidos/producto_form.html`` con el producto
            en edición.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``pedidos:producto_lista`` con un mensaje de éxito.

    Raises:
        Http404: Si no existe ningún producto con esa ``pk`` (lanzado
            por ``get_object_or_404``).
    """
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, ' Producto actualizado correctamente.')
            return redirect('pedidos:producto_lista')
        context = { 'form_producto': form, 'producto_editando': producto, 'seccion_activa': 'producto-editar', }
        return render(request, 'pedidos/producto_form.html', context)

    form = ProductoForm(instance=producto)
    context = { 'form_producto': form, 'producto_editando': producto, 'seccion_activa': 'producto-editar', }
    return render(request, 'pedidos/producto_form.html', context)


@login_required
def producto_eliminar(request, pk):
    """Elimina un producto existente.

    Solo elimina en una petición POST; en GET redirige sin cambios.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado.
        pk (int): Clave primaria del producto a eliminar.

    Returns:
        HttpResponseRedirect: Redirige a ``pedidos:producto_lista``.
            Si la petición fue POST, incluye un mensaje de éxito.

    Raises:
        Http404: Si no existe ningún producto con esa ``pk`` (lanzado
            por ``get_object_or_404``).
    """
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, '🗑️ Producto eliminado.')
    return redirect('pedidos:producto_lista')


def _productos_filtrados(request):
    """Obtiene los productos aplicando los filtros de búsqueda y categoría.

    Args:
        request (HttpRequest): Petición cuyos parámetros GET pueden
            incluir ``q_prod`` (str, texto a buscar en el nombre) y
            ``categoria`` (str, ID de categoría a filtrar).

    Returns:
        QuerySet[Producto]: Productos que cumplen los filtros dados,
            con su categoría precargada (``select_related``).
    """
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
    """Exporta los productos filtrados a un archivo PDF descargable.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta los mismos parámetros de filtro que
            ``_productos_filtrados`` (``q_prod``, ``categoria``).

    Returns:
        HttpResponse: Documento PDF (``content_type='application/pdf'``)
            con cabecera ``Content-Disposition: attachment;
            filename="productos.pdf"``, listo para descarga directa.
    """
    productos_qs = _productos_filtrados(request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="productos.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=1 * cm, rightMargin=1 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles   = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Reporte de Productos", styles['Title']))
    elements.append(Spacer(1, 0.5 * cm))

    data = [['#', 'Nombre', 'Categoría', 'Precio', 'Descripción', 'Disponible']]

    for i, p in enumerate(productos_qs, start=1):
        data.append([
            f"{i:02d}",
            p.nombre,
            p.categoria.nombre if p.categoria else '—',
            f"${p.precio:,.0f}",
            Paragraph(p.descripcion or '—', styles['Normal']),
            'Sí' if p.disponible else 'No',
        ])

    tabla = Table(
        data,
        colWidths=[1.2*cm, 5*cm, 4*cm, 2.5*cm, 8*cm, 2.5*cm],
        repeatRows=1,
    )
    tabla.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#C0392B')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.HexColor('#F5ECD7')),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 9),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#FDF7EC'), colors.HexColor('#EDE3C8')]),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#D4C4A0')),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
    ]))

    elements.append(tabla)
    doc.build(elements)
    return response


@login_required
def producto_exportar_excel(request):
    """Exporta los productos filtrados a un archivo CSV (compatible con Excel).

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta los mismos parámetros de filtro que
            ``_productos_filtrados`` (``q_prod``, ``categoria``).

    Returns:
        HttpResponse: Archivo CSV (``content_type='text/csv;
            charset=utf-8-sig'``) con cabecera
            ``Content-Disposition: attachment; filename="productos.csv"``.
    """
    productos_qs = _productos_filtrados(request)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="productos.csv"'

    writer = csv.writer(response)
    writer.writerow(['#', 'Nombre', 'Categoría', 'Precio', 'Descripción', 'Disponible'])

    for i, p in enumerate(productos_qs, start=1):
        writer.writerow([
            f"{i:02d}",
            p.nombre,
            p.categoria.nombre if p.categoria else '—',
            p.precio,
            p.descripcion or '—',
            'Sí' if p.disponible else 'No',
        ])

    return response


# ── GESTIÓN DE CATEGORÍAS ──────────────────────────────────────────

@login_required
def categoria_lista(request):
    """Lista las categorías, con filtro opcional por nombre.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta el parámetro opcional ``q_cat`` (str): texto a
            buscar en el nombre de la categoría.

    Returns:
        HttpResponse: Renderiza ``pedidos/categoria_lista.html`` con
            el contexto ``{'categorias': QuerySet[Categoria],
            'q_cat': str}``.
    """
    q_cat = request.GET.get('q_cat', '').strip()

    categorias_qs = Categoria.objects.all()
    if q_cat:
        categorias_qs = categorias_qs.filter(nombre__icontains=q_cat)

    context = { 'titulo': 'Módulo de Pedidos', 'categorias': categorias_qs, 'q_cat': q_cat, 'seccion_activa': 'categoria-lista', }
    return render(request, 'pedidos/categoria_lista.html', context)


@login_required
def categoria_crear(request):
    """Muestra y procesa el formulario de creación de una categoría.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado. En POST debe incluir los campos del
            ``CategoriaForm``.

    Returns:
        HttpResponse: En GET, o en POST con errores de formulario,
            renderiza ``pedidos/categoria_form.html``.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``pedidos:categoria_lista`` con un mensaje de éxito.
    """
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Categoría creada correctamente.')
            return redirect('pedidos:categoria_lista')
        messages.error(request, '❌ Corrige los errores en el formulario.')
        context = { 'form_categoria': form, 'seccion_activa': 'categoria-crear', }
        return render(request, 'pedidos/categoria_form.html', context)

    form = CategoriaForm()
    context = { 'form_categoria': form, 'seccion_activa': 'categoria-crear', }
    return render(request, 'pedidos/categoria_form.html', context)


@login_required
def categoria_editar(request, pk):
    """Muestra y procesa el formulario de edición de una categoría.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado. En POST debe incluir los campos del
            ``CategoriaForm``.
        pk (int): Clave primaria de la categoría a editar.

    Returns:
        HttpResponse: En GET, o en POST con errores de formulario,
            renderiza ``pedidos/categoria_form.html`` con la
            categoría en edición.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``pedidos:categoria_lista`` con un mensaje de éxito.

    Raises:
        Http404: Si no existe ninguna categoría con esa ``pk``
            (lanzado por ``get_object_or_404``).
    """
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Categoría actualizada correctamente.')
            return redirect('pedidos:categoria_lista')
        context = { 'form_categoria': form, 'categoria_editando': categoria, 'seccion_activa': 'categoria-editar', }
        return render(request, 'pedidos/categoria_form.html', context)

    form = CategoriaForm(instance=categoria)
    context = { 'form_categoria': form, 'categoria_editando': categoria, 'seccion_activa': 'categoria-editar', }
    return render(request, 'pedidos/categoria_form.html', context)


@login_required
def categoria_eliminar(request, pk):
    """Elimina una categoría existente.

    Solo elimina en una petición POST; en GET redirige sin cambios.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado.
        pk (int): Clave primaria de la categoría a eliminar.

    Returns:
        HttpResponseRedirect: Redirige a ``pedidos:categoria_lista``.
            Si la petición fue POST, incluye un mensaje de éxito.

    Raises:
        Http404: Si no existe ninguna categoría con esa ``pk``
            (lanzado por ``get_object_or_404``).
    """
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, '🗑️ Categoría eliminada.')
    return redirect('pedidos:categoria_lista')


def _categorias_filtradas(request):
    """Obtiene las categorías aplicando el filtro de búsqueda por nombre.

    Args:
        request (HttpRequest): Petición cuyos parámetros GET pueden
            incluir ``q_cat`` (str, texto a buscar en el nombre).

    Returns:
        QuerySet[Categoria]: Categorías que cumplen el filtro dado.
    """
    q_cat = request.GET.get('q_cat', '').strip()

    qs = Categoria.objects.all()
    if q_cat:
        qs = qs.filter(nombre__icontains=q_cat)
    return qs


@login_required
def categoria_exportar_pdf(request):
    """Exporta las categorías filtradas a un archivo PDF descargable.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta el mismo parámetro de filtro que
            ``_categorias_filtradas`` (``q_cat``).

    Returns:
        HttpResponse: Documento PDF (``content_type='application/pdf'``)
            con cabecera ``Content-Disposition: attachment;
            filename="categorias.pdf"``, listo para descarga directa.
    """
    categorias_qs = _categorias_filtradas(request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="categorias.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=1 * cm, rightMargin=1 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles   = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Reporte de Categorías", styles['Title']))
    elements.append(Spacer(1, 0.5 * cm))

    data = [['#', 'Nombre', 'Descripción']]

    for i, c in enumerate(categorias_qs, start=1):
        data.append([
            f"{i:02d}",
            c.nombre,
            Paragraph(c.descripcion or '—', styles['Normal']),
        ])

    tabla = Table(
        data,
        colWidths=[1.2*cm, 5*cm, 14*cm],
        repeatRows=1,
    )
    tabla.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#C0392B')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.HexColor('#F5ECD7')),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 9),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#FDF7EC'), colors.HexColor('#EDE3C8')]),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#D4C4A0')),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
    ]))

    elements.append(tabla)
    doc.build(elements)
    return response


@login_required
def categoria_exportar_excel(request):
    """Exporta las categorías filtradas a un archivo CSV (compatible con Excel).

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta el mismo parámetro de filtro que
            ``_categorias_filtradas`` (``q_cat``).

    Returns:
        HttpResponse: Archivo CSV (``content_type='text/csv;
            charset=utf-8-sig'``) con cabecera
            ``Content-Disposition: attachment; filename="categorias.csv"``.
    """
    categorias_qs = _categorias_filtradas(request)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="categorias.csv"'

    writer = csv.writer(response)
    writer.writerow(['#', 'Nombre', 'Descripción'])

    for i, c in enumerate(categorias_qs, start=1):
        writer.writerow([
            f"{i:02d}",
            c.nombre,
            c.descripcion or '—',
        ])

    return response


# ── GESTIÓN DE CLIENTES ─────────────────────────────────────────────

@login_required
def cliente_lista(request):
    """Lista los clientes, con filtro opcional por nombre o documento.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta el parámetro opcional ``q_cli`` (str): texto a
            buscar en el nombre completo o en el documento del
            cliente.

    Returns:
        HttpResponse: Renderiza ``pedidos/cliente_lista.html`` con el
            contexto ``{'clientes': QuerySet[Cliente], 'q_cli': str}``.
    """
    q_cli = request.GET.get('q_cli', '').strip()

    clientes_qs = Cliente.objects.all()
    if q_cli:
        clientes_qs = clientes_qs.filter(
            Q(nombre_completo__icontains=q_cli) | Q(documento__icontains=q_cli)
        )

    context = { 'titulo': 'Módulo de Pedidos', 'clientes': clientes_qs, 'q_cli': q_cli, 'seccion_activa': 'cliente-lista', }
    return render(request, 'pedidos/cliente_lista.html', context)


@login_required
def cliente_crear(request):
    """Muestra y procesa el formulario de registro de un cliente nuevo.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado. En POST debe incluir los campos del
            ``ClienteForm``.

    Returns:
        HttpResponse: En GET, o en POST con errores de formulario,
            renderiza ``pedidos/cliente_form.html``.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``pedidos:cliente_lista`` con un mensaje de éxito.
    """
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Cliente registrado correctamente.')
            return redirect('pedidos:cliente_lista')
        messages.error(request, '❌ Corrige los errores en el formulario.')
        context = { 'form_cliente': form, 'seccion_activa': 'cliente-crear', }
        return render(request, 'pedidos/cliente_form.html', context)

    form = ClienteForm()
    context = { 'form_cliente': form, 'seccion_activa': 'cliente-crear', }
    return render(request, 'pedidos/cliente_form.html', context)


@login_required
def cliente_editar(request, pk):
    """Muestra y procesa el formulario de edición de un cliente.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado. En POST debe incluir los campos del
            ``ClienteForm``.
        pk (int): Clave primaria del cliente a editar.

    Returns:
        HttpResponse: En GET, o en POST con errores de formulario,
            renderiza ``pedidos/cliente_form.html`` con el cliente
            en edición.
        HttpResponseRedirect: En POST exitoso, redirige a
            ``pedidos:cliente_lista`` con un mensaje de éxito.

    Raises:
        Http404: Si no existe ningún cliente con esa ``pk`` (lanzado
            por ``get_object_or_404``).
    """
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente actualizado correctamente.')
            return redirect('pedidos:cliente_lista')
        context = { 'form_cliente': form, 'cliente_editando': cliente, 'seccion_activa': 'cliente-editar', }
        return render(request, 'pedidos/cliente_form.html', context)

    form = ClienteForm(instance=cliente)
    context = { 'form_cliente': form, 'cliente_editando': cliente, 'seccion_activa': 'cliente-editar', }
    return render(request, 'pedidos/cliente_form.html', context)


@login_required
def cliente_eliminar(request, pk):
    """Elimina un cliente existente.

    Solo elimina en una petición POST; en GET redirige sin cambios.

    Args:
        request (HttpRequest): Petición GET o POST del usuario
            autenticado.
        pk (int): Clave primaria del cliente a eliminar.

    Returns:
        HttpResponseRedirect: Redirige a ``pedidos:cliente_lista``.
            Si la petición fue POST, incluye un mensaje de éxito.

    Raises:
        Http404: Si no existe ningún cliente con esa ``pk`` (lanzado
            por ``get_object_or_404``).
    """
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, '🗑️ Cliente eliminado.')
    return redirect('pedidos:cliente_lista')


def _clientes_filtrados(request):
    """Obtiene los clientes aplicando el filtro de búsqueda por nombre o documento.

    Args:
        request (HttpRequest): Petición cuyos parámetros GET pueden
            incluir ``q_cli`` (str, texto a buscar en el nombre
            completo o en el documento).

    Returns:
        QuerySet[Cliente]: Clientes que cumplen el filtro dado.
    """
    q_cli = request.GET.get('q_cli', '').strip()

    qs = Cliente.objects.all()
    if q_cli:
        qs = qs.filter(
            Q(nombre_completo__icontains=q_cli) | Q(documento__icontains=q_cli)
        )
    return qs


@login_required
def cliente_exportar_pdf(request):
    """Exporta los clientes filtrados a un archivo PDF descargable.

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta el mismo parámetro de filtro que
            ``_clientes_filtrados`` (``q_cli``).

    Returns:
        HttpResponse: Documento PDF (``content_type='application/pdf'``)
            con cabecera ``Content-Disposition: attachment;
            filename="clientes.pdf"``, listo para descarga directa.
    """
    clientes_qs = _clientes_filtrados(request)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="clientes.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=1 * cm, rightMargin=1 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles   = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Reporte de Clientes", styles['Title']))
    elements.append(Spacer(1, 0.5 * cm))

    data = [['#', 'Nombre Completo', 'Teléfono', 'Documento', 'Dirección']]

    for i, c in enumerate(clientes_qs, start=1):
        data.append([
            f"{i:02d}",
            c.nombre_completo,
            c.telefono or '—',
            f"{c.tipo_documento} {c.documento}",
            Paragraph(c.direccion or '—', styles['Normal']),
        ])

    tabla = Table(
        data,
        colWidths=[1.2*cm, 5*cm, 3.5*cm, 4*cm, 9*cm],
        repeatRows=1,
    )
    tabla.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#C0392B')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.HexColor('#F5ECD7')),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 9),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.HexColor('#FDF7EC'), colors.HexColor('#EDE3C8')]),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#D4C4A0')),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
    ]))

    elements.append(tabla)
    doc.build(elements)
    return response


@login_required
def cliente_exportar_excel(request):
    """Exporta los clientes filtrados a un archivo CSV (compatible con Excel).

    Args:
        request (HttpRequest): Petición GET del usuario autenticado.
            Acepta el mismo parámetro de filtro que
            ``_clientes_filtrados`` (``q_cli``).

    Returns:
        HttpResponse: Archivo CSV (``content_type='text/csv;
            charset=utf-8-sig'``) con cabecera
            ``Content-Disposition: attachment; filename="clientes.csv"``.
    """
    clientes_qs = _clientes_filtrados(request)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="clientes.csv"'

    writer = csv.writer(response)
    writer.writerow(['#', 'Nombre Completo', 'Teléfono', 'Tipo Documento', 'Documento', 'Dirección'])

    for i, c in enumerate(clientes_qs, start=1):
        writer.writerow([
            f"{i:02d}",
            c.nombre_completo,
            c.telefono or '—',
            c.tipo_documento,
            c.documento,
            c.direccion or '—',
        ])

    return response
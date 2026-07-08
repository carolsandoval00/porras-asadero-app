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

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# ── HELPERS DE PERMISOS ─────────────────────────────────────────────

TEMPLATE_PERMISOS = 'usuarios/login.html'
ACCESO_DENEGADO   = {'vista': 'sin_permisos'}

def _es_cajero(request):
    """El cajero solo puede ver pedidos, nada más."""
    return request.user.is_authenticated and request.user.rol == 'CAJERO' and not request.user.is_superuser

def _es_mesero(request):
    """El mesero solo puede ver/crear/editar pedidos y reservas."""
    return request.user.is_authenticated and request.user.rol == 'MESERO' and not request.user.is_superuser

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


def _pedidos_filtrados(request):
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
    total_pedidos      = Pedido.objects.count()
    pedidos_pendientes = Pedido.objects.filter(estado='PREPARACION').count()
    total_productos    = Producto.objects.count()
    total_categorias   = Categoria.objects.count()
    total_clientes     = Cliente.objects.count()

    ultimos_pedidos = list(
        Pedido.objects
        .select_related('cliente', 'mesero', 'mesa')
        .order_by('-fecha_creacion')[:5]
    )[::-1]

    return render(request, 'pedidos/dashboard.html', {
        'titulo': 'Módulo de Pedidos',
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
    q          = request.GET.get('q', '').strip()
    estado_sel = request.GET.get('estado', '').strip()
    pedidos_qs = _pedidos_filtrados(request)
    pedidos_lista_data = list(pedidos_qs)
    pedidos_por_fecha  = []
    for fecha, grupo in groupby(pedidos_lista_data, key=lambda p: p.fecha_creacion.date()):
        items = list(grupo)
        pedidos_por_fecha.append({'fecha': fecha, 'pedidos': items, 'count': len(items)})
    return render(request, 'pedidos/pedido_lista.html', {
        'titulo': 'Módulo de Pedidos',
        'pedidos_por_fecha': pedidos_por_fecha,
        'estados': Pedido.ESTADO_CHOICES,
        'q': q,
        'estado_sel': estado_sel,
        'seccion_activa': 'pedido-lista',
    })


@login_required
def pedido_exportar_pdf(request):
    pedidos_qs = _pedidos_filtrados(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="pedidos.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles   = getSampleStyleSheet()
    elements = [Paragraph("Reporte de Pedidos", styles['Title']), Spacer(1, 0.5*cm)]
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
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="pedidos.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Cliente', 'Mesa', 'Productos', 'Descripción', 'Estado', 'Total', 'Fecha'])
    for p in pedidos_qs:
        productos_str = ', '.join(f"{it.cantidad}x {it.producto.nombre}" for it in p.items.all()) or '—'
        writer.writerow([p.numero_pedido, str(p.cliente), str(p.mesa) if p.mesa else '—',
            productos_str, p.descripcion or '—', p.get_estado_display(),
            p.total, p.fecha_creacion.strftime('%d/%m/%Y %H:%M')])
    return response


@login_required
def pedido_crear(request):
    # Cajero NO puede crear pedidos
    if _es_cajero(request):
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
            pedido.save()
            PedidoItem.objects.bulk_create([
                PedidoItem(pedido=pedido, producto=it['producto'],
                    cantidad=it['cantidad'], precio_unitario=it['producto'].precio)
                for it in items_data])
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
    if _es_cajero(request):
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
                p.total = total; p.subtotal = total; p.save()
                pedido.items.all().delete()
                PedidoItem.objects.bulk_create([
                    PedidoItem(pedido=pedido, producto=it['producto'],
                        cantidad=it['cantidad'], precio_unitario=it['producto'].precio)
                    for it in items_data])
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
    if _es_cajero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Pedido eliminado.')
    return redirect('pedidos:pedido_lista')


# ── GESTIÓN DE ÓRDENES ──────────────────────────────────────────────

@login_required
def orden_lista(request):
    # Cajero y Mesero NO pueden ver órdenes
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)

    q_orden = request.GET.get('q_orden', '').strip()
    ordenes_qs = (Pedido.objects.select_related('cliente', 'mesero', 'mesa').order_by('fecha_creacion'))
    if q_orden:
        clean_q = q_orden.replace('ORD-', '').lstrip('0')
        if clean_q.isdigit():
            ordenes_qs = ordenes_qs.filter(Q(id=int(clean_q)) | Q(cliente__nombre_completo__icontains=q_orden))
        else:
            ordenes_qs = ordenes_qs.filter(cliente__nombre_completo__icontains=q_orden)
    ordenes_lista_data = list(ordenes_qs)
    ordenes_por_fecha  = []
    for fecha, grupo in groupby(ordenes_lista_data, key=lambda o: o.fecha_creacion.date()):
        items = list(grupo)
        ordenes_por_fecha.append({'fecha': fecha, 'ordenes': items, 'count': len(items)})
    return render(request, 'pedidos/orden_lista.html', {
        'titulo': 'Módulo de Pedidos', 'ordenes_por_fecha': ordenes_por_fecha,
        'q_orden': q_orden, 'seccion_activa': 'orden-lista'})


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
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.delete()
        messages.success(request, '🗑️ Orden eliminada.')
    return redirect('pedidos:orden_lista')


# ── GESTIÓN DE PRODUCTOS ─────────────────────────────────────────────

@login_required
def producto_lista(request):
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    q_prod  = request.GET.get('q_prod', '').strip()
    cat_sel = request.GET.get('categoria', '').strip()
    productos_qs = Producto.objects.select_related('categoria').all()
    if q_prod:
        productos_qs = productos_qs.filter(nombre__icontains=q_prod)
    if cat_sel:
        productos_qs = productos_qs.filter(categoria__id=cat_sel)
    return render(request, 'pedidos/producto_lista.html', {
        'titulo': 'Módulo de Pedidos', 'productos': productos_qs,
        'categorias': Categoria.objects.all(), 'q_prod': q_prod,
        'cat_sel': cat_sel, 'seccion_activa': 'producto-lista'})


@login_required
def producto_crear(request):
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    productos_qs = _productos_filtrados(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="productos.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Reporte de Productos", styles['Title']), Spacer(1, 0.5*cm)]
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
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    productos_qs = _productos_filtrados(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="productos.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Nombre', 'Categoría', 'Precio', 'Descripción', 'Disponible'])
    for i, p in enumerate(productos_qs, start=1):
        writer.writerow([f"{i:02d}", p.nombre, p.categoria.nombre if p.categoria else '—',
            p.precio, p.descripcion or '—', 'Sí' if p.disponible else 'No'])
    return response


# ── GESTIÓN DE CATEGORÍAS ──────────────────────────────────────────

@login_required
def categoria_lista(request):
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    q_cat = request.GET.get('q_cat', '').strip()
    categorias_qs = Categoria.objects.all()
    if q_cat:
        categorias_qs = categorias_qs.filter(nombre__icontains=q_cat)
    return render(request, 'pedidos/categoria_lista.html', {
        'titulo': 'Módulo de Pedidos', 'categorias': categorias_qs,
        'q_cat': q_cat, 'seccion_activa': 'categoria-lista'})


@login_required
def categoria_crear(request):
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    categorias_qs = _categorias_filtradas(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="categorias.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Reporte de Categorías", styles['Title']), Spacer(1, 0.5*cm)]
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
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    categorias_qs = _categorias_filtradas(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="categorias.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Nombre', 'Descripción'])
    for i, c in enumerate(categorias_qs, start=1):
        writer.writerow([f"{i:02d}", c.nombre, c.descripcion or '—'])
    return response


# ── GESTIÓN DE CLIENTES ─────────────────────────────────────────────

@login_required
def cliente_lista(request):
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    q_cli = request.GET.get('q_cli', '').strip()
    clientes_qs = Cliente.objects.all()
    if q_cli:
        clientes_qs = clientes_qs.filter(
            Q(nombre_completo__icontains=q_cli) | Q(documento__icontains=q_cli))
    return render(request, 'pedidos/cliente_lista.html', {
        'titulo': 'Módulo de Pedidos', 'clientes': clientes_qs,
        'q_cli': q_cli, 'seccion_activa': 'cliente-lista'})


@login_required
def cliente_crear(request):
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
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
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    clientes_qs = _clientes_filtrados(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="clientes.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Reporte de Clientes", styles['Title']), Spacer(1, 0.5*cm)]
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
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    clientes_qs = _clientes_filtrados(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="clientes.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Nombre Completo', 'Teléfono', 'Tipo Documento', 'Documento', 'Dirección'])
    for i, c in enumerate(clientes_qs, start=1):
        writer.writerow([f"{i:02d}", c.nombre_completo, c.telefono or '—',
            c.tipo_documento, c.documento, c.direccion or '—'])
    return response


# ── EXPORTACIÓN DE ÓRDENES ───────────────────────────────────────────

def _ordenes_filtradas(request):
    q_orden = request.GET.get('q_orden', '').strip()
    qs = (Pedido.objects.select_related('cliente', 'mesero', 'mesa')
        .prefetch_related('items__producto').order_by('fecha_creacion'))
    if q_orden:
        clean_q = q_orden.replace('ORD-', '').lstrip('0')
        if clean_q.isdigit():
            qs = qs.filter(Q(id=int(clean_q)) | Q(cliente__nombre_completo__icontains=q_orden))
        else:
            qs = qs.filter(cliente__nombre_completo__icontains=q_orden)
    return qs


@login_required
def orden_exportar_pdf(request):
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    ordenes_qs = _ordenes_filtradas(request)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="ordenes.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4),
        leftMargin=1*cm, rightMargin=1*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Reporte de Órdenes Comerciales", styles['Title']), Spacer(1, 0.5*cm)]
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
    if _es_cajero(request) or _es_mesero(request):
        return render(request, TEMPLATE_PERMISOS, ACCESO_DENEGADO)
    ordenes_qs = _ordenes_filtradas(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="ordenes.csv"'
    writer = csv.writer(response)
    writer.writerow(['Número','Cliente','Mesa','Productos','Estado','Subtotal','Impuesto','Total','Fecha'])
    for o in ordenes_qs:
        productos_str = ', '.join(f"{it.cantidad}x {it.producto.nombre}" for it in o.items.all()) or '—'
        writer.writerow([o.numero_orden, str(o.cliente), str(o.mesa) if o.mesa else '—',
            productos_str, o.get_estado_display(), o.subtotal, o.impuesto, o.total,
            o.fecha_creacion.strftime('%d/%m/%Y %H:%M')])
    return response
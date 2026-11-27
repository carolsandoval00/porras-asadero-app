"""
Pone en ROJO el asterisco (*) de los campos obligatorios en reservas y pedidos.

Uso (desde la carpeta del proyecto, donde esta manage.py):
    python agregar_asteriscos.py

- Solo cambia las lineas de los <label> listadas abajo.
- Si una linea ya tiene el asterisco rojo, la salta.
- Para deshacer todo:  git checkout -- reservas pedidos
"""
import os

STAR = '<span class="req-star" style="color:#C0392B;">*</span>'

def con_estrella(label):
    # '<label ...>Texto *</label>'  ->  '<label ...>Texto <span ...>*</span></label>'
    if label.endswith(' *</label>'):
        return label[:-len(' *</label>')] + ' ' + STAR + '</label>'
    return label[:-len('</label>')] + ' ' + STAR + '</label>'

R = 'reservas/templates/reservas/'
P = 'pedidos/templates/pedidos/'

CAMBIOS = {
    R + 'crear_reserva.html': [
        '<label class="mc-label">Nombre completo *</label>',
        '<label class="mc-label">N.° de personas *</label>',
        '<label class="mc-label">Fecha *</label>',
        '<label class="mc-label">Hora *</label>',
        '<label class="mc-label">Mesa *</label>',
    ],
    R + 'gestion_mesas.html': [
        '<label class="mc-label">Número de mesa *</label>',
        '<label class="mc-label">Capacidad (personas) *</label>',
    ],
    R + 'actualizar_mesa.html': [
        '<label class="mc-label">Capacidad (personas) *</label>',
    ],
    R + 'eliminar_detalle.html': [
        '<label class="mc-label" for="ed-select">Reserva *</label>',
    ],
    P + 'pedido_form.html': [
        '<label>Cliente</label>',
        '<label for="id_mesero">Mesero</label>',
        '<label>Tipo de Pedido</label>',
    ],
    P + 'producto_form.html': [
        '<label>Nombre del Producto</label>',
        '<label>Categoría</label>',
        '<label>Precio ($)</label>',
    ],
    P + 'categoria_form.html': [
        '<label>Nombre de la Categoría</label>',
    ],
    P + 'cliente_form.html': [
        '<label>Nombre Completo</label>',
        '<label>Tipo de Documento</label>',
        '<label>Número de Documento</label>',
        '<label>Teléfono de Contacto</label>',
    ],
}

for ruta, labels in CAMBIOS.items():
    if not os.path.exists(ruta):
        print(f'NO ENCONTRADO  {ruta}')
        continue
    with open(ruta, encoding='utf-8', newline='') as f:
        s = f.read()
    cambiados = 0
    for viejo in labels:
        nuevo = con_estrella(viejo)
        if nuevo in s:
            continue                       # ya estaba hecho
        n = s.count(viejo)
        if n == 0:
            print(f'  - no encontre: {viejo}   ({ruta})')
            continue
        if n > 1:
            print(f'  - aparece {n} veces, revisalo a mano: {viejo}   ({ruta})')
            continue
        s = s.replace(viejo, nuevo)
        cambiados += 1
    if cambiados:
        with open(ruta, 'w', encoding='utf-8', newline='') as f:
            f.write(s)
    print(f'OK  {ruta}: {cambiados} cambio(s)')
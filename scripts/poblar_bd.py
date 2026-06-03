import sys
import os

# Añadir el directorio raíz del proyecto al path
sys.path.append(os.getcwd())

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from datetime import date, time
from django.utils import timezone
from usuarios.models import Usuario, Cliente
from reservas.models import Mesa, Reserva
from pedidos.models import Categoria, Producto, Pedido, PedidoItem
from pago.models import Caja, Pago

def poblar_base_datos():
    print("=== INICIANDO LIMPIEZA Y POBLACIÓN DE LA BASE DE DATOS (MER DEFINITIVO) ===")
    
    # 1. Limpieza de datos en orden inverso de dependencias para evitar violaciones de clave foránea
    print("Limpiando base de datos...")
    Pago.objects.all().delete()
    Caja.objects.all().delete()
    PedidoItem.objects.all().delete()
    Pedido.objects.all().delete()
    Reserva.objects.all().delete()
    Mesa.objects.all().delete()
    Producto.objects.all().delete()
    Categoria.objects.all().delete()
    Cliente.objects.all().delete()
    Usuario.objects.all().delete()
    print("Base de datos limpia con éxito.")

    # 2. Siembra de Usuarios
    print("\nSembrando Usuarios...")
    
    # Superusuario / Administrador solicitado por el usuario
    # Username: 0000000000, Pass: @dmin123
    admin_user = Usuario.objects.create_superuser(
        username='0000000000',
        email='admin@porras.com',
        password='@dmin123',
        first_name='Admin',
        last_name='Staff',
        rol='ADMIN',
        tipo_documento='CC',
        documento='0000000000',
        telefono='3000000000'
    )
    print(f"[OK] Administrador Staff creado: usuario='0000000000', contraseña='@dmin123'")

    # Cajero de prueba
    cajero_user = Usuario.objects.create_user(
        username='martha_cajera',
        email='martha@porras.com',
        password='admin',
        first_name='Martha',
        last_name='Ríos',
        rol='CAJERO',
        tipo_documento='CC',
        documento='50607080',
        telefono='3102223333'
    )
    print(f"[OK] Cajera de prueba creada: usuario='martha_cajera', contraseña='admin'")

    # Mesero de prueba
    mesero_user = Usuario.objects.create_user(
        username='pedrito_mesero',
        email='pedro@porras.com',
        password='admin',
        first_name='Pedro',
        last_name='Gómez',
        rol='MESERO',
        tipo_documento='CC',
        documento='10203040',
        telefono='3154445555'
    )
    print(f"[OK] Mesero de prueba creado: usuario='pedrito_mesero', contraseña='admin'")

    # 3. Siembra de Clientes (según MER)
    print("\nSembrando Clientes...")
    cli1 = Cliente.objects.create(
        nombre_completo='Andrés Rojas',
        telefono='3204567890',
        tipo_documento='CC',
        documento='1057888999',
        direccion='Calle 15 #12-34, Sogamoso'
    )
    cli2 = Cliente.objects.create(
        nombre_completo='María Consuelo',
        telefono='3118765432',
        tipo_documento='CC',
        documento='40012345',
        direccion='Carrera 11 #18-90, Sogamoso'
    )
    cli_paso = Cliente.objects.create(
        nombre_completo='Cliente de Paso',
        telefono='0000000000',
        tipo_documento='CC',
        documento='99999999',
        direccion='Sogamoso'
    )
    print(f"[OK] {Cliente.objects.count()} clientes creados.")

    # 4. Siembra de Mesas (según MER)
    print("\nSembrando Mesas...")
    mesa1 = Mesa.objects.create(numero_mesa=1, capacidad=4, ubicacion='Zona Ventana Principal', estado='LIBRE')
    mesa2 = Mesa.objects.create(numero_mesa=2, capacidad=8, ubicacion='Terraza de las Flores', estado='RESERVADA')
    mesa3 = Mesa.objects.create(numero_mesa=3, capacidad=6, ubicacion='Zona VIP', estado='OCUPADA')
    print(f"[OK] {Mesa.objects.count()} mesas creadas.")

    # 5. Siembra de Reservas (según MER)
    print("\nSembrando Reservas...")
    reserva1 = Reserva.objects.create(
        fecha_reserva=date(2026, 5, 30),
        hora_reserva=time(13, 0, 0),
        numero_personas=8,
        estado='CONFIRMADA',
        cliente=cli2,
        numero_mesa=mesa2
    )
    reserva2 = Reserva.objects.create(
        fecha_reserva=date(2026, 5, 31),
        hora_reserva=time(19, 30, 0),
        numero_personas=4,
        estado='PENDIENTE',
        cliente=cli1,
        numero_mesa=mesa1
    )
    print(f"[OK] {Reserva.objects.count()} reservas creadas.")

    # 6. Siembra de Categorías (según MER)
    print("\nSembrando Categorías...")
    cat1 = Categoria.objects.create(nombre="Carnes al Carbón", descripcion="Cortes premium preparados a la brasa y leña")
    cat2 = Categoria.objects.create(nombre="Sopas", descripcion="Sopas tradicionales de la casa en porciones completas o medias")
    cat3 = Categoria.objects.create(nombre="Platos a la Carta", descripcion="Platos preparados al carbón o a la parrilla")
    cat4 = Categoria.objects.create(nombre="Bebidas", descripcion="Gaseosas, jugos naturales y limonadas")
    print(f"[OK] {Categoria.objects.count()} categorías creadas.")

    # 7. Siembra de Productos (según MER)
    print("\nSembrando Productos...")
    # Carnes al Carbón
    prod1 = Producto.objects.create(nombre="1 Carne al Carbón", categoria=cat1, precio=42000.00, descripcion="Porción completa a la brasa", disponible=True)
    prod2 = Producto.objects.create(nombre="1/2 Carne al Carbón", categoria=cat1, precio=32000.00, descripcion="Media porción a la brasa", disponible=True)
    
    # Sopas
    prod3 = Producto.objects.create(nombre="1 Sopa", categoria=cat2, precio=10000.00, descripcion="Porción completa", disponible=True)
    prod4 = Producto.objects.create(nombre="1/2 Sopa", categoria=cat2, precio=5000.00, descripcion="Media porción", disponible=True)

    # Platos a la Carta
    prod5 = Producto.objects.create(nombre="Pechuga", categoria=cat3, precio=35000.00, descripcion="Asada al carbón", disponible=True)
    prod6 = Producto.objects.create(nombre="Trucha", categoria=cat3, precio=35000.00, descripcion="Fresca y a la brasa", disponible=True)
    prod7 = Producto.objects.create(nombre="Mojarra", categoria=cat3, precio=35000.00, descripcion="A la parrilla", disponible=True)
    prod8 = Producto.objects.create(nombre="Gallina", categoria=cat3, precio=45000.00, descripcion="Tradicional y jugosa", disponible=True)

    # Bebidas
    prod9 = Producto.objects.create(nombre="Limonada Natural", categoria=cat4, precio=4000.00, descripcion="Fresca y natural", disponible=True)
    prod10 = Producto.objects.create(nombre="Gaseosa 350ml", categoria=cat4, precio=3000.00, descripcion="Todas las marcas", disponible=True)
    prod11 = Producto.objects.create(nombre="Gaseosa 1.5L", categoria=cat4, precio=8000.00, descripcion="Para compartir", disponible=True)
    prod12 = Producto.objects.create(nombre="Gaseosa 3L", categoria=cat4, precio=10000.00, descripcion="Familiar", disponible=True)
    prod13 = Producto.objects.create(nombre="Cerveza", categoria=cat4, precio=4000.00, descripcion="Bien fría", disponible=True)
    print(f"[OK] {Producto.objects.count()} productos creados.")

    # 8. Siembra de Cajas (según MER)
    print("\nSembrando Cajas...")
    caja1 = Caja.objects.create(
        monto_inicial=200000.00,
        cajero=admin_user,
        estado='ABIERTA',
        observaciones='Caja matutina inicializada para pruebas'
    )
    print(f"[OK] {Caja.objects.count()} cajas creadas.")

    # 9. Siembra de Pedidos y PedidosItems (según MER)
    print("\nSembrando Pedidos y Detalles...")
    # Pedido 1001 (se creará con PK=1001 para coincidir con el MER si es posible, o tomamos el auto)
    p1 = Pedido.objects.create(
        id=1001,
        cliente=cli2,
        mesero=mesero_user,
        mesa=mesa3,
        tipo_pedido='LOCAL',
        estado='SERVIDO',
        subtotal=88000.00,
        impuestos=0.00,
        total=88000.00
    )
    
    # Items para Pedido 1
    PedidoItem.objects.create(pedido=p1, producto=prod1, cantidad=2, precio_unitario=42000.00, notas="Término medio, papas cocidas") # prod1 is 1 Carne al Carbón
    PedidoItem.objects.create(pedido=p1, producto=prod9, cantidad=1, precio_unitario=4000.00, notas="Con poco hielo") # prod9 is Limonada Natural

    # Pedido 1002
    p2 = Pedido.objects.create(
        id=1002,
        cliente=cli1,
        mesero=mesero_user,
        mesa=None,
        tipo_pedido='DOMICILIO',
        estado='PREPARACION',
        subtotal=46000.00,
        impuestos=0.00,
        total=46000.00
    )
    
    # Items para Pedido 2
    PedidoItem.objects.create(pedido=p2, producto=prod1, cantidad=1, precio_unitario=42000.00, notas="Bien asada, empacar por separado")
    PedidoItem.objects.create(pedido=p2, producto=prod9, cantidad=1, precio_unitario=4000.00, notas="")
    
    print(f"[OK] {Pedido.objects.count()} pedidos y sus items creados.")

    # 10. Siembra de Pagos (según MER)
    print("\nSembrando Pagos...")
    pago1 = Pago.objects.create(
        id=701,
        pedido=p1,
        caja=caja1,
        metodo_pago='EFECTIVO',
        monto=88000.00,
        referencia='',
        descripcion='Pago completo de la comanda en efectivo'
    )
    # Marcar el pedido 1 como PAGADO
    p1.estado = 'PAGADO'
    p1.save()
    
    print(f"[OK] {Pago.objects.count()} pagos creados.")

    print("\n=== ¡SIEMBRA DE DATOS COMPLETADA CON ÉXITO! ===")
    print("\nCredenciales del Administrador de pruebas:")
    print(" - Usuario: 0000000000")
    print(" - Contraseña: @dmin123")
    print("========================================================================\n")

if __name__ == '__main__':
    poblar_base_datos()

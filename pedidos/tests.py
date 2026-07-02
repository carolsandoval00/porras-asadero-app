from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Categoria, Producto, Pedido, PedidoItem

Usuario = get_user_model()


class CategoriaModelTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre="Carnes",
            descripcion="Cortes a la parrilla"
        )

    def test_creacion_categoria(self):
        self.assertEqual(self.categoria.nombre, "Carnes")
        self.assertEqual(Categoria.objects.count(), 1)

    def test_str_categoria(self):
        self.assertEqual(str(self.categoria), "Carnes")


class ProductoModelTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Bebidas")
        self.producto = Producto.objects.create(
            nombre="Limonada",
            categoria=self.categoria,
            precio=Decimal("8000.00"),
            descripcion="Limonada natural",
        )

    def test_creacion_producto(self):
        self.assertEqual(self.producto.nombre, "Limonada")
        self.assertTrue(self.producto.disponible)
        self.assertEqual(self.producto.categoria, self.categoria)

    def test_str_producto(self):
        self.assertEqual(str(self.producto), "Limonada ($8000.00)")

    def test_producto_relacionado_con_categoria(self):
        self.assertIn(self.producto, self.categoria.productos.all())


class PedidoModelTest(TestCase):
    def setUp(self):
        self.mesero = Usuario.objects.create_user(
            username="mesero1",
            password="clave12345",
        )
        self.categoria = Categoria.objects.create(nombre="Carnes")
        self.producto = Producto.objects.create(
            nombre="Costilla",
            categoria=self.categoria,
            precio=Decimal("25000.00"),
        )
        self.pedido = Pedido.objects.create(
            mesero=self.mesero,
            tipo_pedido="LOCAL",
            estado="PREPARACION",
        )

    def test_creacion_pedido(self):
        self.assertEqual(self.pedido.mesero, self.mesero)
        self.assertEqual(self.pedido.estado, "PREPARACION")
        self.assertIsNone(self.pedido.cliente)

    def test_numero_orden(self):
        self.assertEqual(self.pedido.numero_orden, f"ORD-{self.pedido.id:05d}")

    def test_impuesto_property(self):
        self.pedido.impuestos = Decimal("1000.00")
        self.pedido.save()
        self.assertEqual(self.pedido.impuesto, Decimal("1000.00"))

    def test_notas_property(self):
        self.pedido.descripcion = "Sin cebolla"
        self.pedido.save()
        self.assertEqual(self.pedido.notas, "Sin cebolla")

    def test_str_pedido_sin_cliente(self):
        self.assertIn("Cliente de Paso", str(self.pedido))


class PedidoItemModelTest(TestCase):
    def setUp(self):
        self.mesero = Usuario.objects.create_user(
            username="mesero2",
            password="clave12345",
        )
        self.categoria = Categoria.objects.create(nombre="Carnes")
        self.producto = Producto.objects.create(
            nombre="Chorizo",
            categoria=self.categoria,
            precio=Decimal("6000.00"),
        )
        self.pedido = Pedido.objects.create(
            mesero=self.mesero,
            estado="PREPARACION",
        )
        self.item = PedidoItem.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=3,
            precio_unitario=self.producto.precio,
        )

    def test_creacion_item(self):
        self.assertEqual(self.item.cantidad, 3)
        self.assertEqual(self.item.precio_unitario, Decimal("6000.00"))

    def test_subtotal_item(self):
        self.assertEqual(self.item.subtotal, Decimal("18000.00"))

    def test_str_item(self):
        self.assertEqual(str(self.item), "3x Chorizo")


class SignalActualizarPedidoTest(TestCase):
    """Prueba la señal que recalcula el total del pedido al cambiar el precio de un producto."""

    def setUp(self):
        self.mesero = Usuario.objects.create_user(
            username="mesero3",
            password="clave12345",
        )
        self.categoria = Categoria.objects.create(nombre="Carnes")
        self.producto = Producto.objects.create(
            nombre="Pechuga",
            categoria=self.categoria,
            precio=Decimal("15000.00"),
        )
        self.pedido = Pedido.objects.create(
            mesero=self.mesero,
            estado="PREPARACION",
        )
        self.item = PedidoItem.objects.create(
            pedido=self.pedido,
            producto=self.producto,
            cantidad=2,
            precio_unitario=self.producto.precio,
        )
        self.pedido.total = Decimal("30000.00")
        self.pedido.subtotal = Decimal("30000.00")
        self.pedido.save()

    def test_actualiza_total_si_pedido_en_preparacion(self):
        self.producto.precio = Decimal("20000.00")
        self.producto.save()  # dispara la señal post_save

        self.item.refresh_from_db()
        self.pedido.refresh_from_db()

        self.assertEqual(self.item.precio_unitario, Decimal("20000.00"))
        self.assertEqual(self.pedido.total, Decimal("40000.00"))
        self.assertEqual(self.pedido.subtotal, Decimal("40000.00"))

    def test_no_actualiza_total_si_pedido_no_esta_en_preparacion(self):
        self.pedido.estado = "PAGADO"
        self.pedido.save()

        self.producto.precio = Decimal("99999.00")
        self.producto.save()

        self.item.refresh_from_db()
        self.pedido.refresh_from_db()

        # El item conserva su precio original porque el pedido ya no está en preparación
        self.assertEqual(self.item.precio_unitario, Decimal("15000.00"))
        self.assertEqual(self.pedido.total, Decimal("30000.00"))

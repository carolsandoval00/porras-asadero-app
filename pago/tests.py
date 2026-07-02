# pago/tests.py

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Caja, Pago
from pedidos.models import Pedido  

Usuario = get_user_model()


class CajaModelTest(TestCase):
    """Pruebas para el modelo Caja."""

    def setUp(self):
        self.cajero = Usuario.objects.create_user(
            username='cajero_test',
            password='clave12345'
        )

    def test_crear_caja_con_valores_por_defecto(self):
        caja = Caja.objects.create(
            monto_inicial=Decimal('50000.00'),
            cajero=self.cajero
        )
        self.assertEqual(caja.estado, 'ABIERTA')
        self.assertIsNone(caja.fecha_cierre)
        self.assertEqual(caja.observaciones, '')
        self.assertIsNotNone(caja.fecha_apertura)

    def test_str_caja_con_cajero(self):
        caja = Caja.objects.create(
            monto_inicial=Decimal('30000.00'),
            cajero=self.cajero
        )
        esperado = f'Caja #{caja.pk} – {self.cajero.username} – Abierta'
        self.assertEqual(str(caja), esperado)

    def test_cerrar_caja_actualiza_estado_y_fecha(self):
        caja = Caja.objects.create(
            monto_inicial=Decimal('20000.00'),
            cajero=self.cajero
        )
        caja.estado = 'CERRADA'
        caja.fecha_cierre = timezone.now()
        caja.save()

        caja.refresh_from_db()
        self.assertEqual(caja.estado, 'CERRADA')
        self.assertIsNotNone(caja.fecha_cierre)

    def test_ordering_por_fecha_apertura_descendente(self):
        caja1 = Caja.objects.create(monto_inicial=Decimal('10000'), cajero=self.cajero)
        caja2 = Caja.objects.create(monto_inicial=Decimal('20000'), cajero=self.cajero)

        cajas = list(Caja.objects.all())
        self.assertEqual(cajas[0], caja2)  # la más reciente primero
        self.assertEqual(cajas[1], caja1)

    def test_eliminar_cajero_elimina_caja_en_cascada(self):
        caja = Caja.objects.create(monto_inicial=Decimal('15000'), cajero=self.cajero)
        caja_id = caja.pk
        self.cajero.delete()
        self.assertFalse(Caja.objects.filter(pk=caja_id).exists())

    def test_choices_estado_validas(self):
        estados_validos = [choice[0] for choice in Caja.ESTADO_CAJA_CHOICES]
        self.assertIn('ABIERTA', estados_validos)
        self.assertIn('CERRADA', estados_validos)


class PagoModelTest(TestCase):
    """Pruebas para el modelo Pago."""

    def setUp(self):
        self.cajero = Usuario.objects.create_user(
            username='cajero_pago',
            password='clave12345'
        )
        self.caja = Caja.objects.create(
            monto_inicial=Decimal('50000.00'),
            cajero=self.cajero
        )
        # AJUSTA estos campos según los campos reales de tu modelo Pedido
        self.pedido = Pedido.objects.create(
            # mesa=1,
            # estado='PENDIENTE',
            # total=Decimal('25000.00'),
        )

    def test_crear_pago_con_valores_por_defecto(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            caja=self.caja
        )
        self.assertEqual(pago.metodo_pago, 'EFECTIVO')
        self.assertEqual(pago.monto, Decimal('0'))
        self.assertEqual(pago.referencia, '')
        self.assertEqual(pago.descripcion, '')
        self.assertIsNotNone(pago.fecha_pago)

    def test_str_pago(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            caja=self.caja,
            monto=Decimal('35000.00')
        )
        self.assertEqual(str(pago), f'Pago #{pago.pk} – $35000.00')

    def test_metodo_pago_choices_validas(self):
        metodos_validos = [choice[0] for choice in Pago.METODO_PAGO_CHOICES]
        self.assertEqual(metodos_validos, ['EFECTIVO', 'TARJETA', 'TRANSFERENCIA'])

    def test_relacion_pago_con_caja(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            caja=self.caja,
            metodo_pago='TARJETA',
            monto=Decimal('40000.00')
        )
        self.assertIn(pago, self.caja.pagos.all())

    def test_relacion_pago_con_pedido(self):
        pago = Pago.objects.create(
            pedido=self.pedido,
            caja=self.caja,
            monto=Decimal('10000.00')
        )
        self.assertIn(pago, self.pedido.pagos.all())

    def test_eliminar_caja_elimina_pago_en_cascada(self):
        pago = Pago.objects.create(pedido=self.pedido, caja=self.caja)
        pago_id = pago.pk
        self.caja.delete()
        self.assertFalse(Pago.objects.filter(pk=pago_id).exists())

    def test_eliminar_pedido_elimina_pago_en_cascada(self):
        pago = Pago.objects.create(pedido=self.pedido, caja=self.caja)
        pago_id = pago.pk
        self.pedido.delete()
        self.assertFalse(Pago.objects.filter(pk=pago_id).exists())

    def test_ordering_por_fecha_pago_descendente(self):
        pago1 = Pago.objects.create(pedido=self.pedido, caja=self.caja, monto=Decimal('1000'))
        pago2 = Pago.objects.create(pedido=self.pedido, caja=self.caja, monto=Decimal('2000'))

        pagos = list(Pago.objects.all())
        self.assertEqual(pagos[0], pago2)
        self.assertEqual(pagos[1], pago1)


class CajaPagoIntegracionTest(TestCase):
    """Prueba de integración: varios pagos sobre una misma caja."""

    def setUp(self):
        self.cajero = Usuario.objects.create_user(
            username='cajero_integracion',
            password='clave12345'
        )
        self.caja = Caja.objects.create(
            monto_inicial=Decimal('100000.00'),
            cajero=self.cajero
        )
        self.pedido = Pedido.objects.create()  # ajusta campos obligatorios

    def test_suma_de_pagos_registrados_en_caja(self):
        Pago.objects.create(pedido=self.pedido, caja=self.caja, monto=Decimal('20000'))
        Pago.objects.create(pedido=self.pedido, caja=self.caja, monto=Decimal('30000'))

        total = sum(p.monto for p in self.caja.pagos.all())
        self.assertEqual(total, Decimal('50000'))
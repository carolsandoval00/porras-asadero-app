from datetime import date, time

from django.test import TestCase

from .models import Mesa, Reserva
from usuarios.models import Cliente


class MesaModelTest(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(
            numero_mesa=1,
            capacidad=4,
            ubicacion="Terraza",
        )

    def test_creacion_mesa(self):
        self.assertEqual(self.mesa.numero_mesa, 1)
        self.assertEqual(self.mesa.capacidad, 4)
        self.assertEqual(self.mesa.ubicacion, "Terraza")

    def test_estado_por_defecto(self):
        self.assertEqual(self.mesa.estado, "LIBRE")

    def test_str_mesa(self):
        self.assertEqual(str(self.mesa), "Mesa 1")

    def test_cambio_estado_mesa(self):
        self.mesa.estado = "OCUPADA"
        self.mesa.save()
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.estado, "OCUPADA")


class ReservaModelTest(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(
            numero_mesa=5,
            capacidad=6,
            ubicacion="Salón principal",
        )
        self.cliente = Cliente.objects.create(
            nombre_completo="Carolina Pérez",
            telefono="3001234567",
            tipo_documento="CC",
            documento="1029384756",
        )
        self.reserva = Reserva.objects.create(
            fecha_reserva=date(2026, 7, 15),
            hora_reserva=time(19, 30),
            numero_personas=4,
            cliente=self.cliente,
            numero_mesa=self.mesa,
        )

    def test_creacion_reserva(self):
        self.assertEqual(self.reserva.numero_personas, 4)
        self.assertEqual(self.reserva.cliente, self.cliente)
        self.assertEqual(self.reserva.numero_mesa, self.mesa)

    def test_estado_por_defecto(self):
        self.assertEqual(self.reserva.estado, "PENDIENTE")

    def test_nombre_usuario_con_cliente(self):
        self.assertEqual(self.reserva.nombre_usuario, "Carolina Pérez")

    def test_str_reserva(self):
        self.assertEqual(
            str(self.reserva),
            f"Reserva {self.reserva.id} - Carolina Pérez"
        )

    def test_reserva_relacionada_con_mesa(self):
        self.assertIn(self.reserva, self.mesa.reservas.all())

    def test_reserva_relacionada_con_cliente(self):
        self.assertIn(self.reserva, self.cliente.reservas.all())

    def test_cambio_estado_a_confirmada(self):
        self.reserva.estado = "CONFIRMADA"
        self.reserva.save()
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "CONFIRMADA")

    def test_cambio_estado_a_cancelada(self):
        self.reserva.estado = "CANCELADA"
        self.reserva.save()
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado, "CANCELADA")

    def test_eliminar_mesa_elimina_reserva(self):
        """on_delete=CASCADE: si se borra la mesa, se borra la reserva asociada."""
        mesa_id = self.mesa.numero_mesa
        self.mesa.delete()
        self.assertFalse(Reserva.objects.filter(pk=self.reserva.pk).exists())

    def test_eliminar_cliente_elimina_reserva(self):
        """on_delete=CASCADE: si se borra el cliente, se borra la reserva asociada."""
        self.cliente.delete()
        self.assertFalse(Reserva.objects.filter(pk=self.reserva.pk).exists())
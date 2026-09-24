"""Pruebas del módulo de reservas: API, filtros por fecha, permisos y vistas."""
import json
from datetime import date, timedelta

from django.test import Client, TestCase
from django.urls import reverse

from reservas.models import Mesa, Reserva
from usuarios.models import Usuario


class ReservasTest(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username='admin1', email='a@a.com', password='x', rol='ADMIN')
        self.cajero = Usuario.objects.create_user(
            username='caja1', email='c@c.com', password='x', rol='CAJERO')
        self.m1 = Mesa.objects.create(numero_mesa=1, capacidad=4, ubicacion='Salón principal')
        self.m2 = Mesa.objects.create(numero_mesa=2, capacidad=2, ubicacion='Salón secundario')
        self.c = Client()
        self.c.force_login(self.admin)
        self.manana = (date.today() + timedelta(days=1)).isoformat()
        self.otro = (date.today() + timedelta(days=5)).isoformat()

    def _crear(self, **kw):
        datos = {
            'nombre_cliente': 'María García', 'telefono': '3001234567',
            'email': 'm@g.com', 'numero_personas': 2,
            'fecha_reserva': self.manana, 'hora_reserva': '19:00',
            'numero_mesa': 1, 'estado': 'CONFIRMADA', 'ocasion': '', 'notas': '',
        }
        datos.update(kw)
        return self.c.post(reverse('reserva_guardar'), json.dumps(datos),
                           content_type='application/json')

    def test_crear_reserva_persiste_en_bd(self):
        r = self._crear()
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()['ok'])
        self.assertEqual(Reserva.objects.count(), 1)
        reserva = Reserva.objects.first()
        self.assertEqual(reserva.nombre_cliente, 'María García')
        # la mesa queda marcada como reservada
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, 'RESERVADA')

    def test_mesa_ocupada_rechaza_doble_reserva(self):
        self._crear()
        r = self._crear(nombre_cliente='Otro', telefono='3009998888')
        self.assertEqual(r.status_code, 400)
        self.assertIn('ya está reservada', r.json()['error'])
        self.assertEqual(Reserva.objects.count(), 1)

    def test_capacidad_insuficiente(self):
        r = self._crear(numero_mesa=2, numero_personas=6)
        self.assertEqual(r.status_code, 400)
        self.assertIn('capacidad', r.json()['error'])

    def test_telefono_debe_tener_10_digitos(self):
        r = self._crear(telefono='300')
        self.assertEqual(r.status_code, 400)
        self.assertIn('10 dígitos', r.json()['error'])

    def test_fecha_pasada_rechazada(self):
        r = self._crear(fecha_reserva=(date.today() - timedelta(days=2)).isoformat())
        self.assertEqual(r.status_code, 400)

    def test_editar_reserva(self):
        self._crear()
        reserva = Reserva.objects.first()
        r = self._crear(id=reserva.id, numero_personas=4, estado='PENDIENTE')
        self.assertEqual(r.status_code, 200, r.content)
        reserva.refresh_from_db()
        self.assertEqual(reserva.numero_personas, 4)
        self.assertEqual(reserva.estado, 'PENDIENTE')
        self.assertEqual(Reserva.objects.count(), 1)

    def test_eliminar_reserva(self):
        self._crear()
        reserva = Reserva.objects.first()
        r = self.c.post(reverse('reserva_eliminar'), json.dumps({'id': reserva.id}),
                        content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Reserva.objects.count(), 0)
        self.m1.refresh_from_db()
        self.assertEqual(self.m1.estado, 'LIBRE')

    # ── FILTRO POR FECHAS ────────────────────────────────────
    def test_filtro_por_rango_de_fechas(self):
        self._crear()
        self._crear(fecha_reserva=self.otro, numero_mesa=2, numero_personas=2)
        self.assertEqual(Reserva.objects.count(), 2)

        url = reverse('api_reservas')
        todas = self.c.get(url).json()
        self.assertEqual(todas['total'], 2)

        solo_manana = self.c.get(url, {'fecha': 'rango', 'desde': self.manana,
                                       'hasta': self.manana}).json()
        self.assertEqual(solo_manana['total'], 1)
        self.assertEqual(solo_manana['reservas'][0]['fecha'], self.manana)

        rango_completo = self.c.get(url, {'fecha': 'rango', 'desde': self.manana,
                                          'hasta': self.otro}).json()
        self.assertEqual(rango_completo['total'], 2)

        desde_futuro = self.c.get(url, {'desde': self.otro}).json()
        self.assertEqual(desde_futuro['total'], 1)

    def test_filtro_dia_mes_y_pasadas(self):
        self._crear()
        url = reverse('api_reservas')
        self.assertEqual(self.c.get(url, {'fecha': 'dia', 'dia': self.manana}).json()['total'], 1)
        self.assertEqual(self.c.get(url, {'fecha': 'dia', 'dia': self.otro}).json()['total'], 0)
        self.assertEqual(self.c.get(url, {'fecha': 'mes', 'mes': self.manana[:7]}).json()['total'], 1)
        self.assertEqual(self.c.get(url, {'fecha': 'pasadas'}).json()['total'], 0)
        self.assertEqual(self.c.get(url, {'fecha': 'futuras'}).json()['total'], 1)

    def test_filtro_por_texto_y_estado(self):
        self._crear()
        url = reverse('api_reservas')
        self.assertEqual(self.c.get(url, {'q': 'María'}).json()['total'], 1)
        self.assertEqual(self.c.get(url, {'q': '3001234567'}).json()['total'], 1)
        self.assertEqual(self.c.get(url, {'q': 'Pepito'}).json()['total'], 0)
        self.assertEqual(self.c.get(url, {'estado': 'CONFIRMADA'}).json()['total'], 1)
        self.assertEqual(self.c.get(url, {'estado': 'CANCELADA'}).json()['total'], 0)

    # ── MESAS ────────────────────────────────────────────────
    def test_mesa_guardar_y_eliminar(self):
        r = self.c.post(reverse('mesa_guardar'),
                        json.dumps({'numero_mesa': 9, 'capacidad': 6,
                                    'ubicacion': 'Terraza', 'estado': 'LIBRE'}),
                        content_type='application/json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(Mesa.objects.filter(numero_mesa=9).exists())

        r = self.c.post(reverse('mesa_eliminar'), json.dumps({'numero_mesa': 9}),
                        content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Mesa.objects.filter(numero_mesa=9).exists())

    def test_api_mesas(self):
        datos = self.c.get(reverse('api_mesas')).json()
        self.assertEqual(len(datos['mesas']), 2)
        self.assertEqual(datos['mesas'][0]['numero'], 1)

    # ── PERMISOS ─────────────────────────────────────────────
    def test_cajero_puede_ver_pero_no_guardar(self):
        c = Client()
        c.force_login(self.cajero)
        self.assertEqual(c.get(reverse('api_reservas')).status_code, 200)
        r = c.post(reverse('reserva_guardar'), json.dumps({}), content_type='application/json')
        self.assertEqual(r.status_code, 403)

    def test_anonimo_redirige_a_login(self):
        c = Client()
        self.assertEqual(c.get(reverse('api_reservas')).status_code, 302)

    # ── VISTAS HTML ──────────────────────────────────────────
    def test_paginas_html_cargan(self):
        for nombre in ['reserva_inicio', 'crear_reserva', 'eliminar_detalle',
                       'listar_mesas', 'diagrama_mesas', 'gestion_mesas']:
            r = self.c.get(reverse(nombre))
            self.assertEqual(r.status_code, 200, f'{nombre} → {r.status_code}')

    def test_eliminar_detalle_post_borra(self):
        self._crear()
        reserva = Reserva.objects.first()
        r = self.c.post(reverse('eliminar_detalle'), {'detalle': reserva.id})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_editar_reserva_html(self):
        self._crear()
        reserva = Reserva.objects.first()
        r = self.c.get(reverse('editar_reserva', args=[reserva.pk]))
        self.assertEqual(r.status_code, 200)
        r = self.c.post(reverse('editar_reserva', args=[reserva.pk]), {
            'nombre_cliente': 'Nuevo Nombre', 'telefono': '3001112222', 'email': '',
            'fecha_reserva': self.manana, 'hora_reserva': '19:00',
            'numero_personas': 3, 'ocasion': '', 'estado': 'CONFIRMADA',
            'notas': '', 'numero_mesa': 1,
        })
        self.assertEqual(r.status_code, 302)
        reserva.refresh_from_db()
        self.assertEqual(reserva.nombre_cliente, 'Nuevo Nombre')
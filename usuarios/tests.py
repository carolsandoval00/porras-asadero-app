from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from usuarios.models import Cliente, Usuario


# ── USUARIO ──────────────────────────────────────────────────────────

class UsuarioModelTest(TestCase):

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='jperez',
            email='jperez@example.com',
            password='clave12345',
            first_name='Juan',
            last_name='Pérez',
            telefono='3001234567',
            tipo_documento='CC',
            documento='1010101010',
            rol='MESERO',
        )

    def test_creacion_basica(self):
        self.assertEqual(Usuario.objects.count(), 1)
        self.assertEqual(self.usuario.username, 'jperez')
        self.assertEqual(self.usuario.email, 'jperez@example.com')
        self.assertTrue(self.usuario.check_password('clave12345'))

    def test_str_representation(self):
        esperado = f"{self.usuario.first_name} {self.usuario.last_name} ({self.usuario.username})"
        self.assertEqual(str(self.usuario), esperado)
        self.assertEqual(str(self.usuario), 'Juan Pérez (jperez)')

    def test_rol_por_defecto(self):
        usuario_sin_rol = Usuario.objects.create_user(
            username='sinrol',
            email='sinrol@example.com',
            password='clave12345',
        )
        self.assertEqual(usuario_sin_rol.rol, 'MESERO')

    def test_tipo_documento_por_defecto(self):
        usuario_sin_tipo = Usuario.objects.create_user(
            username='sintipo',
            email='sintipo@example.com',
            password='clave12345',
        )
        self.assertEqual(usuario_sin_tipo.tipo_documento, 'CC')

    def test_rol_choices_validas(self):
        roles_validos = [r[0] for r in Usuario.ROLE_CHOICES]
        self.assertEqual(roles_validos, ['ADMIN', 'CAJERO', 'MESERO'])
        self.assertIn(self.usuario.rol, roles_validos)

    def test_tipo_documento_choices_validas(self):
        tipos_validos = [t[0] for t in Usuario.TIPO_DOCUMENTO_CHOICES]
        self.assertEqual(tipos_validos, ['CC', 'CE', 'TI', 'PP'])

    def test_email_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Usuario.objects.create_user(
                    username='otrouser',
                    email='jperez@example.com',  # mismo email
                    password='otraclave123',
                )

    def test_documento_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Usuario.objects.create_user(
                    username='otrouser2',
                    email='otro@example.com',
                    password='otraclave123',
                    documento='1010101010',  # mismo documento
                )

    def test_documento_puede_ser_nulo(self):
        usuario_sin_doc = Usuario.objects.create_user(
            username='sindoc',
            email='sindoc@example.com',
            password='clave12345',
        )
        self.assertIsNone(usuario_sin_doc.documento)

    def test_telefono_opcional(self):
        usuario_sin_tel = Usuario.objects.create_user(
            username='sintel',
            email='sintel@example.com',
            password='clave12345',
        )
        self.assertIsNone(usuario_sin_tel.telefono)

    def test_foto_opcional(self):
        self.assertFalse(self.usuario.foto)

    def test_required_fields_incluye_email(self):
        self.assertIn('email', Usuario.REQUIRED_FIELDS)

    def test_creacion_superusuario(self):
        admin = Usuario.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminclave123',
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_actualizar_rol(self):
        self.usuario.rol = 'ADMIN'
        self.usuario.save()
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.rol, 'ADMIN')


# ── CLIENTE ──────────────────────────────────────────────────────────

class ClienteModelTest(TestCase):

    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre_completo='María Gómez',
            telefono='3109876543',
            tipo_documento='CC',
            documento='2020202020',
            direccion='Calle 10 #20-30',
        )

    def test_creacion_basica(self):
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(self.cliente.nombre_completo, 'María Gómez')
        self.assertEqual(self.cliente.documento, '2020202020')

    def test_str_representation(self):
        self.assertEqual(str(self.cliente), 'María Gómez')

    def test_direccion_opcional(self):
        cliente_sin_direccion = Cliente.objects.create(
            nombre_completo='Carlos Ruiz',
            telefono='3001112233',
            tipo_documento='CC',
            documento='3030303030',
        )
        self.assertIsNone(cliente_sin_direccion.direccion)

    def test_documento_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cliente.objects.create(
                    nombre_completo='Otro Cliente',
                    telefono='3200000000',
                    tipo_documento='CE',
                    documento='2020202020',  # mismo documento que self.cliente
                )

    def test_actualizar_telefono(self):
        self.cliente.telefono = '3115550000'
        self.cliente.save()
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.telefono, '3115550000')

    def test_eliminar_cliente(self):
        cliente_id = self.cliente.pk
        self.cliente.delete()
        self.assertFalse(Cliente.objects.filter(pk=cliente_id).exists())

    def test_multiples_clientes_distintos_documentos(self):
        Cliente.objects.create(
            nombre_completo='Ana Torres',
            telefono='3123334455',
            tipo_documento='CC',
            documento='4040404040',
        )
        self.assertEqual(Cliente.objects.count(), 2)
from django.db import models
from django.db import models
from django.contrib.auth.models import User

class Usuario(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15)

    def __str__(self):
        return self.nombre
        return self.nombre

ROLES_CHOICES = [
    ('ADMIN', 'Administrador'),
    ('MESERO', 'Mesero'),
    ('COCINA', 'Personal de Cocina'),
    ('CAJA', 'Cajero'),
]

class PerfilUsuario(models.Model):
    # Relacionamos este perfil con el usuario de Django
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    
    # Campos adicionales para Porras Asadero
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono de contacto")
    rol = models.CharField(max_length=20, choices=ROLES_CHOICES, default='MESERO')
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección de residencia")
    fecha_nacimiento = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.get_rol_display()}"

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"

class Personal(models.Model):
    ROLES = [
        ('admin', 'Administrador'),
        ('mesero', 'Mesero'),
        ('cajero', 'Cajero'),
    ]

    nombre = models.CharField(max_length=100)
    usuario = models.CharField(max_length=50, unique=True)
    contraseña = models.CharField(max_length=100)
    rol = models.CharField(max_length=10, choices=ROLES)

    def __str__(self):
        return self.nombre


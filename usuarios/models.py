from django.db import models
from django.db import models
from django.contrib.auth.models import AbstractUser, User


class Usuario(AbstractUser):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15)

    ROLE_CHOICES = [
    ('ADMIN', 'Administrador'),
    ('MESERO', 'Mesero'),
    ('COCINA', 'Personal de Cocina'),
    ('CAJA', 'Cajero'),
    ]

    TIPO_DOCUMENTO_CHOICES = [
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PP', 'Pasaporte'),
    ]
    first_name = models.CharField(max_length=150, blank=False, verbose_name='Nombres')
    last_name = models.CharField(max_length=150, blank=False, verbose_name='Apellidos')
    
    tipo_documento = models.CharField(max_length=2, choices=TIPO_DOCUMENTO_CHOICES, verbose_name='Tipo de Documento')
    documento = models.CharField(max_length=20, unique=True, verbose_name='Número de Documento')
    rol = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MESERO', verbose_name='Rol del Usuario')
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name}"



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


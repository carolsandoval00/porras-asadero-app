from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    email = models.EmailField(unique=True, verbose_name='Correo electrónico')
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name='Teléfono')
    
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
    
    tipo_documento = models.CharField(
        max_length=2, 
        choices=TIPO_DOCUMENTO_CHOICES,
        default='CC',
        verbose_name='Tipo de Documento'
    )
    documento = models.CharField(
        max_length=20, 
        unique=True,
        blank=True, 
        null=True,
        verbose_name='Número de Documento'
    )
    rol = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='MESERO', 
        verbose_name='Rol del Usuario'
    )
    
    
    foto = models.ImageField(
        upload_to='fotos_perfil/',
        blank=True,
        null=True,
        verbose_name='Foto de perfil'
    )

    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
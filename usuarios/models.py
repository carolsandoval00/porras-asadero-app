from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado para el Asadero.
    AbstractUser ya incluye: username, password, is_staff, is_active, date_joined.
    """
    # Sobrescribimos email para hacerlo único y obligatorio
    email = models.EmailField(unique=True, verbose_name='Correo electrónico')
    
    # Campos adicionales específicos
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

    # Sobrescribimos nombres y apellidos para que aparezcan correctamente en formularios
    first_name = models.CharField(max_length=150, verbose_name='Nombres')
    last_name = models.CharField(max_length=150, verbose_name='Apellidos')
    
    tipo_documento = models.CharField(
        max_length=2, 
        choices=TIPO_DOCUMENTO_CHOICES, 
        verbose_name='Tipo de Documento'
    )
    documento = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name='Número de Documento'
    )
    rol = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='MESERO', 
        verbose_name='Rol del Usuario'
    )

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"

# Nota: He mantenido la clase Personal por si la usas en otra parte del código,
# pero lo ideal es usar solo la clase 'Usuario' para todo lo relacionado con el equipo.
class Personal(models.Model):
    ROLES = [
        ('admin', 'Administrador'),
        ('mesero', 'Mesero'),
        ('cajero', 'Cajero'),
    ]

    nombre = models.CharField(max_length=100)
    usuario = models.CharField(max_length=50, unique=True)
    # Importante: No guardes contraseñas en texto plano. Django no cifra este campo 'contraseña'.
    contraseña = models.CharField(max_length=100) 
    rol = models.CharField(max_length=10, choices=ROLES)

    def __str__(self):
        return self.nombre
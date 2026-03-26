from django.db import models

class Usuario(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15)

    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('mesero', 'Mesero'),
        ('cajero', 'Cajero'),
    ]

    rol = models.CharField(max_length=10, choices=ROL_CHOICES, default='mesero')

    def __str__(self):
        return self.nombre
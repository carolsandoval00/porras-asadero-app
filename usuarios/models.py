from django.db import models

class Usuario(models.Model):
    codigo = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=200)
    correo = models.EmailField()
    rol = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

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
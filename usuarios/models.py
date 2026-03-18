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

from django.db import models

class Usuario(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15)

    def __str__(self):
        return self.nombre
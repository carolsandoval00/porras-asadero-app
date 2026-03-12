from django.db import models

class Mesa(models.Model):
    numero_mesa = models.IntegerField(primary_key=True)
    capacidad = models.IntegerField()
    ubicacion = models.CharField(max_length=100)
    estado = models.CharField(max_length=50)

    def __str__(self):
        return f"Mesa {self.numero_mesa}"


class Reserva(models.Model):
    numero_reserva = models.AutoField(primary_key=True)
    hora_reserva = models.TimeField()
    numero_personas = models.IntegerField()
    nombre_usuario = models.CharField(max_length=100)

    mesa = models.ForeignKey(
        Mesa,
        on_delete=models.CASCADE,
        related_name='reservas'
    )

    def __str__(self):
        return f"Reserva {self.numero_reserva}"


class DetalleReserva(models.Model):
    codigo = models.AutoField(primary_key=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    hora = models.TimeField()

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='detalles'
    )

    def __str__(self):
        return f"Detalle {self.codigo}"
    

from django.db import models


# ✅ ESTE TE FALTABA
class Mesa(models.Model):
    numero_mesa = models.IntegerField(primary_key=True)
    capacidad = models.IntegerField()
    ubicacion = models.CharField(max_length=100)
    estado = models.CharField(max_length=50)

    def __str__(self):
        return f"Mesa {self.numero_mesa}"


class Reserva(models.Model):
    numero = models.AutoField(primary_key=True, verbose_name='Número')
    hora_reserva = models.TimeField(verbose_name='Hora de la Reserva')
    numero_personas = models.IntegerField(verbose_name='Número de Personas')
    nombre_usuario = models.CharField(max_length=100, verbose_name='Nombre del Usuario')

    numero_mesa = models.ForeignKey(
    'Mesa',
    on_delete=models.CASCADE,
    related_name='reservas',
    null=True,
    blank=True
)

    numero_reserva = models.IntegerField(verbose_name='Número de Reserva')

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'

    def __str__(self):
        return f"Reserva {self.numero} - {self.nombre_usuario}"


class DetalleReserva(models.Model):
    codigo = models.AutoField(primary_key=True, verbose_name='Código')
    fecha_inicio = models.DateField(verbose_name='Fecha Inicio')
    fecha_fin = models.DateField(verbose_name='Fecha Fin')
    hora = models.TimeField(verbose_name='Hora')

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Reserva'
    )

    class Meta:
        verbose_name = 'Detalle de Reserva'
        verbose_name_plural = 'Detalles de Reserva'

    def __str__(self):
        return f"Detalle {self.codigo} - Reserva {self.reserva.numero}"
    
from django.db import models

class Mesa(models.Model):
    ESTADO_MESA_CHOICES = [
        ('LIBRE', 'Libre'),
        ('OCUPADA', 'Ocupada'),
        ('RESERVADA', 'Reservada'),
    ]
    numero_mesa = models.IntegerField(primary_key=True)
    capacidad = models.IntegerField()
    ubicacion = models.CharField(max_length=100)
    estado = models.CharField(
        max_length=50, 
        choices=ESTADO_MESA_CHOICES, 
        default='LIBRE'
    )

    def __str__(self):
        return f"Mesa {self.numero_mesa}"


class Reserva(models.Model):
    ESTADO_RESERVA_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADA', 'Confirmada'),
        ('CANCELADA', 'Cancelada'),
    ]
    id = models.AutoField(primary_key=True)
    fecha_reserva = models.DateField(verbose_name='Fecha de la Reserva')
    hora_reserva = models.TimeField(verbose_name='Hora de la Reserva')
    numero_personas = models.IntegerField(verbose_name='Número de Personas')
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_RESERVA_CHOICES, 
        default='PENDIENTE',
        verbose_name='Estado'
    )
    cliente = models.ForeignKey(
        'usuarios.Cliente', 
        on_delete=models.CASCADE, 
        related_name='reservas', 
        verbose_name='Cliente'
    )
    numero_mesa = models.ForeignKey(
        'Mesa',
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name='Mesa'
    )

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'

    @property
    def nombre_usuario(self):
        return self.cliente.nombre_completo if self.cliente else "Sin Cliente"

    def __str__(self):
        return f"Reserva {self.id} - {self.nombre_usuario}"
    
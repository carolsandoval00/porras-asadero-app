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

    class Meta:
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'
        ordering = ['numero_mesa']

    def __str__(self):
        return f"Mesa {self.numero_mesa}"

    def as_dict(self):
        """Representación JSON que consume static/js/reservas.js."""
        return {
            'numero': self.numero_mesa,
            'capacidad': self.capacidad,
            'ubicacion': self.ubicacion,
            'estado': self.estado,
        }


class Reserva(models.Model):
    ESTADO_RESERVA_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADA', 'Confirmada'),
        ('CANCELADA', 'Cancelada'),
    ]
    id = models.AutoField(primary_key=True)

    # Datos del cliente que captura el formulario de la interfaz.
    nombre_cliente = models.CharField(
        max_length=255, default='', verbose_name='Nombre del cliente')
    telefono = models.CharField(
        max_length=15, default='', verbose_name='Teléfono')
    email = models.EmailField(blank=True, default='', verbose_name='Correo electrónico')

    fecha_reserva = models.DateField(verbose_name='Fecha de la Reserva')
    hora_reserva = models.TimeField(verbose_name='Hora de la Reserva')
    numero_personas = models.IntegerField(verbose_name='Número de Personas')
    ocasion = models.CharField(
        max_length=50, blank=True, default='', verbose_name='Ocasión especial')
    notas = models.TextField(blank=True, default='', verbose_name='Notas adicionales')
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_RESERVA_CHOICES,
        default='PENDIENTE',
        verbose_name='Estado'
    )
    creada = models.DateTimeField(
        auto_now_add=True, null=True, verbose_name='Fecha de creación')

    # Opcional: si la reserva corresponde a un cliente ya registrado en el sistema.
    cliente = models.ForeignKey(
        'usuarios.Cliente',
        on_delete=models.SET_NULL,
        related_name='reservas',
        null=True,
        blank=True,
        verbose_name='Cliente registrado'
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
        ordering = ['fecha_reserva', 'hora_reserva']

    @property
    def nombre_usuario(self):
        if self.nombre_cliente:
            return self.nombre_cliente
        if self.cliente:
            return self.cliente.nombre_completo
        return "Sin Cliente"

    def __str__(self):
        return f"Reserva {self.id} - {self.nombre_usuario}"

    def as_dict(self):
        """Representación JSON que consume static/js/reservas.js."""
        return {
            'id': self.id,
            'nombre': self.nombre_usuario,
            'telefono': self.telefono,
            'email': self.email,
            'personas': self.numero_personas,
            'fecha': self.fecha_reserva.isoformat(),
            'hora': self.hora_reserva.strftime('%H:%M'),
            'mesa': self.numero_mesa_id,
            'ocasion': self.ocasion,
            'estado': self.estado,
            'notas': self.notas,
            'creada': self.creada.isoformat() if self.creada else None,
        }
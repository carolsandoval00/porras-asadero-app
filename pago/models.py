from django.db import models

METODO_CHOICES = [
    ('efectivo',      'Efectivo'),
    ('transferencia', 'Transferencia'),
]

ESTADO_CHOICES = [
    ('pendiente', 'Pendiente'),
    ('aprobado',  'Aprobado'),
]


class Pago(models.Model):
    orden       = models.ForeignKey(
                    'pedidos.Orden',
                    on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='pagos'
                  )
    metodo_pago = models.CharField(max_length=50, choices=METODO_CHOICES, default='efectivo')
    monto       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    referencia  = models.CharField(max_length=100, blank=True, default='')
    estado      = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_pago  = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-fecha_pago']

    def __str__(self):
        return f'Pago #{self.pk} – ${self.monto}'


ESTADO_CAJA_CHOICES = [
    ('abierta', 'Abierta'),
    ('cerrada', 'Cerrada'),
]


class Caja(models.Model):
    monto_inicial  = models.DecimalField(max_digits=10, decimal_places=2)
    # CORRECCIÓN: era ForeignKey a Usuario, ahora es CharField de texto libre.
    # El cajero se escribe manualmente en lugar de seleccionarse de la lista de usuarios.
    cajero         = models.CharField(max_length=150, blank=True, default='')
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre   = models.DateTimeField(null=True, blank=True)
    estado         = models.CharField(max_length=10, choices=ESTADO_CAJA_CHOICES, default='abierta')
    observaciones  = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-fecha_apertura']
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'

    def __str__(self):
        return f'Caja #{self.pk} – {self.cajero} – {self.get_estado_display()}'